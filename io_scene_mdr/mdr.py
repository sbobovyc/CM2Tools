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

import numpy as np
import struct
from pprint import pprint


def print4x4matrix(matrix):
    print("[")
    for row in matrix:
        print("[{0: .2f}, {1: .2f}, {2: .2f}, {3: .2f}]".format(row[0], row[1], row[2], row[3]))
    print("]")


def read_matrix(f):
    print("# Start reading matrix", "0x%x" % f.tell())
    mat = np.identity(4)

    # 3x4 matrix, column order
    for column in range(0, 4):
        for row in range(0, 3):
            value, = struct.unpack("f", f.read(4))
            print("# 0x%x [%i] %f" % (f.tell()-4, column, value))
            mat[row][column] = value
    print("# This is a transform matrix:")
    print(mat)
    return mat


def write_matrix(mat, f):
    # 3x4 matrix, column order
    for column in range(0, 4):
        f.write(struct.pack("fff", *mat[column][:3]))


def read_material(f):
    print("# Start reading material", "0x%x" % f.tell())
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
    material_id, = struct.unpack("<I", f.read(4))
    print("# Material id", material_id)  # saved at 005CE8A6
    print("# End material", "0x%x" % f.tell())

    material = {"material_id": material_id, "ambient_color": ambient_color, "diffuse_color": diffuse_color,
                "specular_color": specular_color, "shininess": shininess, "alpha_constant": alpha_constant}
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
            self.num_models, = struct.unpack("<I", f.read(4))
            print("# number of models", self.num_models)
            for i in range(0, self.num_models):
                mdr_obj = MDRObject()
                mdr_obj.read(self.base_name, self.num_models, f, i, outdir, not self.parse_only, self.verbose)
                self.objects.append(mdr_obj)

    def write(self, filepath):
        with open(filepath, "wb") as f:
            self.num_models = len(self.objects)
            f.write(struct.pack("<I", self.num_models))

            for o in self.objects:
                f.write(struct.pack('x'))
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
                f.write(struct.pack('<I', len(o.uv_array)-1))  # last uv index

                f.write(struct.pack('xx'))  # some unknown
                f.write(struct.pack("<H", len(o.parent_name)))
                if len(o.parent_name) > 0:
                    f.write(struct.pack("%is" % len(o.parent_name), o.parent_name))

                write_matrix(o.transform_matrix, f)
                write_matrix(o.inverse_transform_matrix, f)

                f.write(struct.pack("<I", len(o.anchor_points)))
                for anchor in o.anchor_points:
                    name, m = anchor
                    f.write(struct.pack("<H", len(name)))
                    f.write(struct.pack("%is" % len(name), name))
                    write_matrix(m, f)

                f.write(struct.pack(60 * 'x'))  # unknown

                f.write(struct.pack("fff", 1.0, 1.0, 1.0))  # ambient color is hard coded to white
                f.write(struct.pack("fff", *o.material["diffuse_color"]))
                f.write(struct.pack("fff", *o.material["specular_color"]))
                f.write(struct.pack("f", o.material["shininess"]))
                f.write(struct.pack("f", o.material["alpha_constant"]))
                f.write(struct.pack("I", o.material["material_id"]))

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
        self.transform_matrix = None
        self.inverse_transform_matrix = None

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
        f.read(1)  # read at 004537A0
        name_length, = struct.unpack("<H", f.read(2))
        print("# submodel name length:", name_length)
        self.name = f.read(name_length).decode("ascii")  # saved at 0073E054
        print("# submodel name:", self.name)

        unk0, = struct.unpack("b", f.read(1))  # saved at 004539C7
        if unk0 != 2:
            error_message = "unk0 is %s, not 2, 0x%x %s, %s, %s" % (
            unk0, f.tell() - 1, base_name, self.name, model_number)
            # raise ValueError(error_message)
            print(error_message)
        else:
            print("unk0 is %s (always 2?) 0x%x %s, %s, %s" % (unk0, f.tell() - 1, base_name, self.name, model_number))
            
        print("# Start unknown section of 176 bytes, has something to do with collision box", "0x%x" % f.tell())
        self.collision_data = []
        for i in range(0, 10):
            unk, = struct.unpack("f", f.read(4))
            self.collision_data.append(unk)
            if verbose:
                print("# 0x%x [%i] %f" % (f.tell()-4, i, unk))
        unk, = struct.unpack("f", f.read(4))  # saved at 00453AAA
        self.collision_data.append(unk)
        if verbose:
            print("# 0x%x %f" % (f.tell()-4, unk))        
        for i in range(0, 6):
            for j in range(0, 4):
                unk, = struct.unpack("f", f.read(4))
                self.collision_data.append(unk)
                if verbose:
                    print("# 0x%x [%i] %f" % (f.tell()-4, i, unk))
        unk = struct.unpack("fff", f.read(12))
        print("# 0x%x %f %f %f" % (f.tell() - 12, *unk))  # saved at 00453B3C
        self.bbox_x_min, self.bbox_x_max, self.bbox_y_min, self.bbox_y_max, self.bbox_z_min, self.bbox_z_max = struct.unpack("ffffff", f.read(24))  # saved at 00453B4C
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
        face_count, = struct.unpack("<I", f.read(4))  # read at 004537C5
        print("# Face count:", int(face_count / 3))

        for i in range(0, int(face_count / 3)):  # read at 0045397B
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
        print("# UV in section:", int(uv_in_section / 2))

        for i in range(0, int(uv_in_section / 2)):  # read at 00453965
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
        uv_last_index, = struct.unpack("<I", f.read(4))
        print("# Last uv index %i" % uv_last_index, "at 0x%x" % (f.tell()-4))  # saved at 0045381B, right after UV data
        if uv_last_index != uv_in_section/2 - 1:
            print("Last uv index != uv_in_section/2 - 1")

        unk1, = struct.unpack("<H", f.read(2))  # read at 00453826, some kind of a counter?
        print("# Unknown uint16 unk1 0x%x" % unk1, "at 0x%x" % (f.tell() - 4))
        length, = struct.unpack("<H", f.read(2))
        self.parent_name = f.read(length).decode("ascii")
        print("# %s, parent name:" % self.name, self.parent_name, hex(f.tell()))
        
        self.transform_matrix = read_matrix(f)  # read at 004532C1
        self.inverse_transform_matrix = read_matrix(f)  # read at 004532D1

        anchor_point_count, = struct.unpack("<I", f.read(4))  # read at 004532DF
        print("# Read 4 bytes, object count: ", anchor_point_count)

        for i in range(0, anchor_point_count):
            name_length, = struct.unpack("<H", f.read(2))
            anchor_name = f.read(name_length).decode("ascii")
            print("Anchor point %i: %s" % (i, anchor_name))
            m = read_matrix(f)  # read at 00453311
            self.anchor_points.append((anchor_name, m))
        print("# End list of anchor points", "0x%x" % f.tell())

        print("# Start unknown data ", "0x%x" % f.tell())
        for i in range(0, 3):
            f.read(1)  # always 0, read at 00453347, saved at 0045335B
            f.read(1)  # always 0, read at 00453365, saved at 00453378
            f.read(4)  # read at 00453380
            f.read(4)  # read at 00453395

        for i in range(0, 3):
            f.read(1)  # read at 004533CE, saved at 004533E2
            f.read(1)  # read 1 at 004533EC
            f.read(4)  # read 4 at 00453407
            f.read(4)  # read 4 at 0045341C

        print("# End unknown data ", "0x%x" % f.tell())
        
        self.material = read_material(f)  # read at 0045343F, sub_5CE790

        name_length, = struct.unpack("<H", f.read(2))  # read in sub_73DE20, length of string
        texture_name = f.read(name_length).decode("ascii")  # read at 0073DEA3
        print("# Texture name:", texture_name)
        # print("Texture\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s" % (
        # self.material["material_id"], texture_name, self.material["ambient_color"], self.material["diffuse_color"],
        # self.material["specular_color"], self.material["shininess"], self.material["alpha_constant"], self.name))

        if dump:
            self.texture_name = texture_name
        
        unk3, = struct.unpack("b", f.read(1))  # read at 00453462
        if unk3 != 2:
            error_message = error_message = "unk3 is %s, not 2, 0x%x %s, %s, %s" % (
            unk3, f.tell() - 1, base_name, self.name, model_number)
            # raise ValueError(error_message)
            print(error_message)
        else:
            print("unk3 is %s (always 2?) 0x%x %s, %s, %s" % (unk3, f.tell() - 1, base_name, self.name, model_number))
        # read 4, 11 starting at 0045347B
        print("# Start unknown section of 176 bytes, has something to do with collision box", "0x%x" % f.tell())
        for i in range(0, 35):
            unk, = struct.unpack("f", f.read(4))
            self.collision_data.append(unk)
            if verbose:
                print("# 0x%x [%i] %f" % (f.tell() - 4, i, unk))
        unk = struct.unpack("fff", f.read(12))  # read at 004535D7
        print("# 0x%x %f %f %f" % (f.tell() - 12, *unk))  # read at 004535D7
        self.bbox_x_min, self.bbox_x_max, self.bbox_y_min, self.bbox_y_max, self.bbox_z_min, self.bbox_z_max = struct.unpack("ffffff", f.read(24))
        print("# Bound box min/max")  # read at 004535E7
        print("# xmin ", self.bbox_x_min)
        print("# xmax ", self.bbox_x_max)
        print("# ymin ", self.bbox_y_min)
        print("# ymax ", self.bbox_y_max)
        print("# zmin ", self.bbox_z_min)
        print("# zmax ", self.bbox_z_max)
        print("# Finished unknown section", "0x%x" % f.tell())

        print("# Start vertices at 0x%x" % f.tell())
        vertex_floats, = struct.unpack("<I", f.read(4))  # read at 004535FB
        print("# Vertex count:", int(vertex_floats / 3))

        for i in range(0, int(vertex_floats / 3)):  # read at 0045373D
            if not dump:
                f.read(12)
            else:
                x, y, z = struct.unpack("fff", f.read(12))
                self.vertex_array.append((x, y, z))
        print("# End vertices", "0x%x" % f.tell())

        print("# Start vertex normals at 0x%x" % f.tell())
        normal_count, = struct.unpack("<I", f.read(4))  # read at 0045361D
        print("# Normals count:", int(normal_count / 3))  # 3 per vertex

        for i in range(0, int(normal_count / 3)):  # read at 00453727
            if not dump:
                f.read(6)
            else:
                nx, ny, nz = struct.unpack("<hhh", f.read(6))
                if verbose:
                    print("# vn [%i] %i %i %i" % (i, nx, ny, nz))
                self.vertex_normal_array.append((nx, ny, nz))
        print("# End normals", "0x%x" % f.tell())

        footer_counter, = struct.unpack("<I", f.read(4))  # read at 00453649
        if footer_counter != 0:
            print("# Parsing footer, count:", footer_counter)
            print(f.name, self.name)
            for i in range(0, footer_counter):
                print(struct.unpack("<fff", f.read(12)))
                length, = struct.unpack("<I", f.read(4))
                f.read(length * 4)
        print("# End model 0x%x ##############################################################" % f.tell())
