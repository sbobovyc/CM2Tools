# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####

# <pep8 compliant>

# Script copyright (C) Stanislav Bobovych
# Contributors: Stanislav Bobovych

"""
This script imports a Wavefront OBJ files to Blender.

Usage:
Run this script from "File->Import" menu and then load the desired MDR file.
"""

import os
import json
import struct
from pprint import pprint


def print4x4matrix(matrix):
    print("[")
    for row in matrix:
        print("[{0: .2f}, {1: .2f}, {2: .2f}, {3: .2f}]".format(row[0], row[1], row[2], row[3]))
    print("]")


def read_matrix(f):
    print("# Start reading matrix", "0x%x" % f.tell())
    meta = [3*[0] for i in range(4)]
    for i in range(0, 4):
        for j in range(0, 3):
            value, = struct.unpack("f", f.read(4))
            print("# 0x%x [%i] %f" % (f.tell()-4, i, value))
            meta[i][j] = value
    pprint(meta)
    transform_matrix = [ 4*[0] for i in range(4)]
    for i in range(0, 4):
        for j in range(0, 3):
            transform_matrix[j][i] = meta[i][j]
    transform_matrix[3][3] = 1.0
    print("# This is mostly likely this transform matrix:")
    print4x4matrix(transform_matrix)
    print("# End metadata", "0x%x" % f.tell())
    return meta


def read_material(f):
    print("# Start reading material", "0x%x" % f.tell())
    unknown_constants = struct.unpack("ff", f.read(8))
    print("# Unknown constants", unknown_constants)
    ambient_color = struct.unpack("fff", f.read(4 * 3))
    print("# Ambient color", ambient_color)  # GL_AMBIENT
    diffuse_color = struct.unpack("fff", f.read(4 * 3))
    print("# Diffuse color", diffuse_color)  # GL_DIFFUSE
    specular_color = struct.unpack("fff", f.read(4 * 3))
    print("# Specular color", specular_color)  # GL_SPECULAR
    shininess, = struct.unpack("f", f.read(4))
    print("# Shininess", shininess)  # GL_SHININESS
    alpha_constant, = struct.unpack("f", f.read(4))
    print("# Alpha constant", alpha_constant)
    print("# End material", "0x%x" % f.tell())

    material = {}
    material["unknown_constants"] = unknown_constants
    material["ambient_color"] = ambient_color
    material["diffuse_color"] = diffuse_color
    material["specular_color"] = specular_color
    material["shininess"] = shininess
    material["alpha_constant"] = alpha_constant
    return material


class MDR:
    def __init__(self, filepath, base_name, dump_manifest=False, parse_only=False, verbose=False):
        self.filepath = filepath
        self.base_name = base_name
        self.parse_only = parse_only
        self.verbose = verbose
        self.objects = []

        #in the binary file
        self.num_models = 0

    def read(self, outdir):
        with open(self.filepath, "rb") as f:
            self.num_models, = struct.unpack("<Ix", f.read(5))
            print("# number of models", self.num_models)
            for i in range(0, self.num_models):
                mdr_obj = MDRObject()
                mdr_obj.read(self.base_name, self.num_models, f, i, outdir, not self.parse_only, self.verbose)
                self.objects.append(mdr_obj)

    def write(self, filepath):
        with open(filepath, "wb") as f:
            self.num_models = len(self.objects)
            f.write(struct.pack("<Ix", self.num_models))
            model_number = 0
            for o in self.objects:
                f.write(struct.pack("<H", len(o.name)))
                f.write(struct.pack("%is" % len(o.name), o.name))
                f.write(struct.pack("b", 2))  # unk0
                f.write(struct.pack("f", 1.0))  # if the next 176 bytes are all 0, the object can not be moved in the editor
                f.write(struct.pack('x' * 148))
                f.write(struct.pack("ff", o.bbox_x_min, o.bbox_x_max))
                f.write(struct.pack("ff", o.bbox_y_min, o.bbox_y_max))
                f.write(struct.pack("ff", o.bbox_z_min, o.bbox_z_max))
                f.write(struct.pack("<I", 3*len(o.index_array)))
                for idx in o.index_array:
                    f.write(struct.pack("<HHH", idx[0], idx[1], idx[2]))
                f.write(struct.pack("<I", 2*len(o.uv_array)))
                for uv in o.uv_array:
                    f.write(struct.pack("<ff", uv[0], uv[1]))
                f.write(struct.pack('xxxx'))  # some unknown
                if model_number == 0:
                    # read_material
                    f.write(struct.pack("ff", 0, 1.0))
                    f.write(struct.pack("fff", 0, 0, 0))
                    f.write(struct.pack("fff", 1.0, 0, 0))
                    f.write(struct.pack("fff", 0, 1.0, 0))
                    f.write(struct.pack("f", 0))

                    # read_material
                    f.write(struct.pack("ff", 0, 1.0))
                    f.write(struct.pack("fff", 0, 0, 0))
                    f.write(struct.pack("fff", 1.0, 0, 0))
                    f.write(struct.pack("fff", 0, 1.0, 0))
                    f.write(struct.pack("f", 0))

                    f.write(struct.pack("<I", 0))  # unk1
                    f.write(struct.pack("<I", len(o.anchor_points)))
                    for anchor in o.anchor_points:
                        name, m = anchor
                        f.write(struct.pack("<H", len(name)))
                        f.write(struct.pack("%is" % len(name), name))
                        f.write(struct.pack("fff", *m[0][:3]))
                        f.write(struct.pack("fff", *m[1][:3]))
                        f.write(struct.pack("fff", *m[2][:3]))
                        f.write(struct.pack("fff", *m[3][:3]))
                    f.write(struct.pack('xx'))  # 2 bytes padding
                    f.write(struct.pack(48 * 'x'))  # read_material
                    f.write(struct.pack('xx'))  # 2 bytes padding

                    # read_material
                    f.write(struct.pack("ff", 0, 0))
                    f.write(struct.pack("fff", 1.0, 1.0, 1.0))  # ambient color is hard coded to white
                    f.write(struct.pack("fff", *o.material["diffuse_color"]))
                    f.write(struct.pack("fff", *o.material["specular_color"]))
                    f.write(struct.pack("f", o.material["shininess"]))
                    f.write(struct.pack("f", o.material["alpha_constant"]))
                else:
                    f.write(struct.pack("<xxH", len(o.parent_name)))
                    f.write(struct.pack("%is" % len(o.parent_name), o.parent_name))

                    # read_material
                    f.write(struct.pack("ff", 0, 1.0))
                    f.write(struct.pack("fff", 0, 0, 0))
                    f.write(struct.pack("fff", 1.0, 0, 0))
                    f.write(struct.pack("fff", 0, 1.0, 0))
                    f.write(struct.pack("f", 0))

                    # read_material
                    f.write(struct.pack("ff", 0, 1.0))
                    f.write(struct.pack("fff", 0, 0, 0))
                    f.write(struct.pack("fff", 1.0, 0, 0))
                    f.write(struct.pack("fff", 0, 1.0, 0))
                    f.write(struct.pack("f", 0))

                    f.write(struct.pack("<I", len(o.anchor_points)))
                    for anchor in o.anchor_points:
                        name, m = anchor
                        f.write(struct.pack("<H", len(name)))
                        f.write(struct.pack("%is" % len(name), name))
                        f.write(struct.pack("fff", *m[0][:3]))
                        f.write(struct.pack("fff", *m[1][:3]))
                        f.write(struct.pack("fff", *m[2][:3]))
                        f.write(struct.pack("fff", *m[3][:3]))

                    # some unknown, probably actual material info
                    for i in range(0, 15):
                        f.write(struct.pack("f", 0.0))
                    f.write(struct.pack("fff", 1.0, 1.0, 1.0))  # ambient color is hard coded to white
                    f.write(struct.pack("fff", *o.material["diffuse_color"]))
                    f.write(struct.pack("fff", *o.material["specular_color"]))
                    f.write(struct.pack("f", o.material["shininess"]))
                    f.write(struct.pack("f", o.material["alpha_constant"]))

                f.write(struct.pack("<I", 0))  # unk2
                f.write(struct.pack("<H", len(o.texture_name)))
                f.write(struct.pack("%is" % len(o.texture_name), o.texture_name))
                f.write(struct.pack("b", 2))  # unk3
                f.write(struct.pack("f", 1.0))  # if the next 176 bytes are all 0, the object can not be moved in the editor
                f.write(struct.pack('x' * 148))
                f.write(struct.pack("ff", o.bbox_x_min, o.bbox_x_max))
                f.write(struct.pack("ff", o.bbox_y_min, o.bbox_y_max))
                f.write(struct.pack("ff", o.bbox_z_min, o.bbox_z_max))
                f.write(struct.pack("<I", 3*len(o.vertex_array)))
                for vert in o.vertex_array:
                    f.write(struct.pack("<fff", vert[0], vert[1], vert[2]))
                f.write(struct.pack("<I", 3*len(o.vertex_normal_array)))
                for norm in o.vertex_normal_array:
                    f.write(struct.pack("<hhh", norm[0], norm[1], norm[2]))
                f.write(struct.pack("<I", 0))  # no footer
                if model_number < self.num_models-1:
                    f.write(struct.pack('x'))

                model_number += 1



class MDRObject:
    """MDR object
    """
    def __init__(self):
        """The constructor takes a model name as parameter. All other variables are set
        directly.
        """
        self.base_name = ""
        self.name = ""
        self.parent_name = ""
        self.index_array = []   # [ (i,i,i) ...]
        self.uv_array = []      # [ (f,f) ...]        
        self.vertex_array = []  # [ (f,f,f) ...]
        self.vertex_normal_array = []  # [ (i16,i16,i16) ...]
        self.texture_name = ""
        self.material = {}
        self.anchor_points = []  # [ (name, matrix) ...]
        self.bbox_x_min = 0
        self.bbox_x_max = 0
        self.bbox_y_min = 0
        self.bbox_y_max = 0
        self.bbox_z_min = 0
        self.bbox_z_max = 0

    def read(self, base_name, num_models, f, model_number, outdir, dump=True, verbose=False):
        ########
        # object:
        # face indices
        # UVs,
        # then,
        # vertices (in object space?)
        # then,
        # normals
        ####
        self.base_name = base_name
        print("# Start model %i" % model_number, "at 0x%x" % f.tell(),
              "##############################################################")
        name_length, = struct.unpack("<H", f.read(2))
        print("# submodel name length:", name_length)
        self.name = f.read(name_length).decode("ascii")
        print("# submodel name:", self.name)

        unk0, = struct.unpack("b", f.read(1))
        if unk0 != 2:
            error_message = "unk0 is %s, not 2, 0x%x %s, %s, %s" % (
            unk0, f.tell() - 1, base_name, self.name, model_number)
            # raise ValueError(error_message)
            print(error_message)
        else:
            print("unk0 is %s (always 2?) 0x%x %s, %s, %s" % (unk0, f.tell() - 1, base_name, self.name, model_number))
            
        print("# Start unknown section of 176 bytes, has something to do with collision box", "0x%x" % f.tell())
        self.collision_data = []
        for i in range(0, 38):
            unk, = struct.unpack("f", f.read(4))
            self.collision_data.append(unk)
            if verbose:
                print("# [%i] %f" % (i, unk))
        self.bbox_x_min, self.bbox_x_max, self.bbox_y_min, self.bbox_y_max, self.bbox_z_min, self.bbox_z_max = struct.unpack("ffffff", f.read(24))
        print("# Bound box min/max")
        print("# xmin ", self.bbox_x_min)
        print("# xmax ", self.bbox_x_max)
        print("# ymin ", self.bbox_y_min)
        print("# ymax ", self.bbox_y_max)
        print("# zmin ", self.bbox_z_min)
        print("# zmax ", self.bbox_z_max)
        print("# Finished unknown section", "0x%x" % f.tell())

        ###############################################
        print("# Start face vertex indices at 0x%x" % f.tell())
        face_count, = struct.unpack("<I", f.read(4))
        print("# Face count:", face_count / 3)

        for i in range(0, int(face_count / 3)):
            if not dump:
                f.read(6)
            else:
                v0, v1, v2 = struct.unpack("<HHH", f.read(6))
                # print("f %i/%i %i/%i %i/%i" % (v0+1,v0+1,v1+1,v1+1,v2+1,v2+1))
                self.index_array.append((v0, v1, v2))
        print("# Finished face vertex indices", "0x%x" % f.tell())
        ###############################################

        ###############################################
        print("# Start UVs at 0x%x" % f.tell())
        uv_in_section, = struct.unpack("<I", f.read(4))
        print("# UV in section:", uv_in_section / 2)

        for i in range(0, int(uv_in_section / 2)):
            if not dump:
                f.read(8)
            else:
                u, v = struct.unpack("<ff", f.read(8))
                self.uv_array.append((u, v))
                if verbose:
                    print("# vt", i, u,v)
        print("# Finish UV section:", "0x%x" % f.tell())
        ###############################################

        print("# Start unknown section 1")
        unk, = struct.unpack("<I", f.read(4))
        print("# Unknown 0x%x" % unk, "at 0x%x" % (f.tell()-4))

        if model_number == 0:
            read_matrix(f)
            read_matrix(f)

            print("# End unknown section", "0x%x" % f.tell())
            unk1, = struct.unpack("<I", f.read(4))
            if unk1 != 0:
                error_message = error_message = "unk1 is %s, not 0, 0x%x %s, %s, %s" % (
                unk1, f.tell() - 4, base_name, self.name, model_number)
                # raise ValueError(error_message)
                print(error_message)
            else:
                print("unk1 is %s (always 0?) 0x%x %s, %s, %s" % (unk1, f.tell() - 1, base_name, self.name, model_number))                    

            anchor_point_count, = struct.unpack("<I", f.read(4))
            print("# Read 4 bytes, object count: ", anchor_point_count)

            for i in range(0, anchor_point_count):
                name_length, = struct.unpack("<H", f.read(2))
                anchor_name = f.read(name_length).decode("ascii")
                print("Anchor point %i: %s" % (i, anchor_name))
                m = read_matrix(f)
                self.anchor_points.append((anchor_name, m))
            print("# End list of anchor points", "0x%x" % f.tell())
            f.read(2)  # always 0
            print("# random garbage? ", "0x%x" % f.tell())
            read_matrix(f) # this is for sure model wide material
            f.read(2)  # always 0
            meta1_offset = f.tell()
            self.material = read_material(f)
            print("# End section", "0x%x" % f.tell())
        else:
            length, = struct.unpack("<xxH", f.read(4))
            self.parent_name = f.read(length).decode("ascii")
            print("# parent name:", self.parent_name, hex(f.tell()))
            read_matrix(f)
            read_matrix(f)
            anchor_point_count, = struct.unpack("<I", f.read(4))
            print("# Anchor point count", anchor_point_count)
            for i in range(0, anchor_point_count):
                length, = struct.unpack("<H", f.read(2))
                anchor_name = f.read(length).decode("ascii")
                print("# Memory point name:", anchor_name)
                if length != 0:
                    m = read_matrix(f)
                self.anchor_points.append((anchor_name, m))
                print("#End of sub-meta", "0x%x" % f.tell())

            unk = []
            for i in range(0, 13):
                unk.append(*struct.unpack("f", f.read(4)))
                print("0x%x %f" % (f.tell()-4, unk[-1]))

            self.material = read_material(f)
            print("# End section", "0x%x" % f.tell())

        unk2, = struct.unpack("<I", f.read(4))        
        if unk2 != 0:
            error_message = error_message = "unk2 is %s, not 0, 0x%x %s, %s, %s" % (
            unk2, f.tell() - 4, base_name, self.name, model_number)
            # raise ValueError(error_message)
            print(error_message)
        else:
            print("unk2 is %s (always 0?) 0x%x %s, %s, %s" % (unk2, f.tell() - 4, base_name, self.name, model_number))

        name_length, = struct.unpack("<H", f.read(2))
        texture_name = f.read(name_length).decode("ascii")
        print("# Texture name:", texture_name)
        if dump:
            self.texture_name = texture_name

        unk3, = struct.unpack("b", f.read(1))
        if unk3 != 2:
            error_message = error_message = "unk3 is %s, not 2, 0x%x %s, %s, %s" % (
            unk3, f.tell() - 1, base_name, self.name, model_number)
            # raise ValueError(error_message)
            print(error_message)
        else:
            print("unk3 is %s (always 2?) 0x%x %s, %s, %s" % (unk3, f.tell() - 1, base_name, self.name, model_number))

        print("# Start unknown section of 176 bytes, has something to do with collision box", "0x%x" % f.tell())
        self.collision_data = []
        for i in range(0, 38):
            unk, = struct.unpack("f", f.read(4))
            self.collision_data.append(unk)
            if verbose:
                print("# [%i] %f" % (i, unk))
        self.bbox_x_min, self.bbox_x_max, self.bbox_y_min, self.bbox_y_max, self.bbox_z_min, self.bbox_z_max = struct.unpack("ffffff", f.read(24))
        print("# Bound box min/max")
        print("# xmin ", self.bbox_x_min)
        print("# xmax ", self.bbox_x_max)
        print("# ymin ", self.bbox_y_min)
        print("# ymax ", self.bbox_y_max)
        print("# zmin ", self.bbox_z_min)
        print("# zmax ", self.bbox_z_max)
        print("# Finished unknown section", "0x%x" % f.tell())

        ###############################################
        print("# Start vertices at 0x%x" % f.tell())
        vertex_floats, = struct.unpack("<I", f.read(4))
        print("# Vertex count:", vertex_floats / 3)

        for i in range(0, int(vertex_floats / 3)):
            if not dump:
                f.read(12)
            else:
                x, y, z = struct.unpack("fff", f.read(12))
                self.vertex_array.append((x, y, z))
        print("# End vertices", "0x%x" % f.tell())
        ###############################################

        print("# Start vertex normals at 0x%x" % f.tell())
        normal_count, = struct.unpack("<I", f.read(4))
        print("# Normals count:", normal_count / 3)  # 3 per vertex

        for i in range(0, int(normal_count / 3)):
            if not dump:
                f.read(6)
            else:
                nx, ny, nz = struct.unpack("<hhh", f.read(6))
                if verbose:
                    print("# vn [%i] %i %i %i" % (i, nx, ny, nz))
                self.vertex_normal_array.append((nx, ny, nz))
        print("# End normals", "0x%x" % f.tell())
        ###############################################

        unk, = struct.unpack("<I", f.read(4))
        if unk != 0:
            print("# Parsing footer, count:", unk)
            print(f.name, self.name)
            for i in range(0, unk):
                print(struct.unpack("<fff", f.read(12)))
                length, = struct.unpack("<I", f.read(4))
                f.read(length * 4)
        print("# End model ##############################################################")
        f.read(1)
