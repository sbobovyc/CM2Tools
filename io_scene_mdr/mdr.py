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
    print("# Ambient color", ambient_color)
    diffuse_color = struct.unpack("fff", f.read(4 * 3))
    print("# Diffuse color", diffuse_color)
    specular_color = struct.unpack("fff", f.read(4 * 3))
    print("# Specular color", specular_color)
    specular_exponent, = struct.unpack("f", f.read(4))
    print("# Specular exponent", specular_exponent)
    print("# End material", "0x%x" % f.tell())

    material = {}
    material["unknown_constants"] = unknown_constants
    material["ambient_color"] = ambient_color
    material["diffuse_color"] = diffuse_color
    material["specular_color"] = specular_color
    material["specular_exponent"] = specular_exponent
    return material


class MDR:
    def __init__(self, filepath, base_name, dump_manifest=False, parse_only=False, verbose=False):
        self.filepath = filepath
        self.base_name = base_name
        self.parse_only = parse_only
        self.verbose = verbose
        self.objects = []
        self.model_manifests = []
        self.dump_manifest = dump_manifest

        #in the binary file
        self.num_models = 0

    def read(self, outdir):
        with open(self.filepath, "rb") as f:
            self.num_models, = struct.unpack("<Ix", f.read(5))
            print("# number of models", self.num_models)
            for i in range(0, self.num_models):
                mdr_obj = MDRObject()
                manifest = mdr_obj.read(self.base_name, self.num_models, f, i, outdir, not self.parse_only, self.verbose)
                self.objects.append(mdr_obj)
                self.model_manifests.append(manifest)

        if self.dump_manifest and not self.parse_only:
            with open(os.path.join(outdir, "%s_manifest.json" % self.base_name), "w") as f:
                json.dump([u'%s' % self.base_name, self.model_manifests], f, indent=4)

    def write(self, filepath):
        with open(filepath, "wb") as f:
            self.num_models = len(self.objects)
            f.write(struct.pack("<Ix", self.num_models))
            for o in self.objects:
                f.write(struct.pack("<H", len(o.name)))
                f.write(struct.pack("%is" % len(o.name), o.name))
                f.write(struct.pack("b", 2))  # unk0
                f.write(struct.pack('x'*0xB0))
                f.write(struct.pack("<I", 3*len(o.index_array)))
                for idx in o.index_array:
                    f.write(struct.pack("<HHH", idx[0], idx[1], idx[2]))


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
        self.material = None
        self.anchor_points = []  # [ (name, matrix) ...]

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
            
        print("# Start unknown section", "0x%x" % f.tell())
        for i in range(0, int(0xB0 / 4)):
            unk, = struct.unpack("f", f.read(4))
            if verbose:
                print("# [%i] %f" % (i, unk))
        print("# Finished unknown section", "0x%x" % f.tell())

        ###############################################
        print("# Start face vertex indices")
        face_count, = struct.unpack("<I", f.read(4))
        print("# Face count:", face_count / 3)
        manifest = {u'model': base_name, u'sub_model': self.name, u'vertex_index_offset': f.tell()}

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
        print("# Start UVs")
        uv_in_section, = struct.unpack("<I", f.read(4))
        print("# UV in section:", uv_in_section / 2)

        manifest[u'vertex_uv_offset'] = f.tell()

        for i in range(0, int(uv_in_section / 2)):
            if not dump:
                f.read(8)
            else:
                u, v = struct.unpack("<ff", f.read(8))
                # print("vt", u,v)
                self.uv_array.append((u, v))
        print("# Finish UV section:", "0x%x" % f.tell())
        ###############################################

        print("# Start unknown section 1")
        unk, = struct.unpack("<I", f.read(4))
        print("# Unknown 0x%x" % unk, "at 0x%x" % f.tell())

        if model_number == 0:
            read_material(f)
            read_material(f)

            print("# End unknown section", "0x%x" % f.tell())
            unk1, = struct.unpack("<I", f.read(4))
            if unk1 != 0:
                error_message = error_message = "unk1 is %s, not 0, 0x%x %s, %s, %s" % (
                unk1, f.tell() - 4, base_name, self.name, model_number)
                # raise ValueError(error_message)
                print(error_message)
            else:
                print("unk1 is %s (always 0?) 0x%x %s, %s, %s" % (unk1, f.tell() - 1, base_name, self.name, model_number))                    

            object_count, = struct.unpack("<I", f.read(4))
            print("# Read 4 bytes, object count: ", object_count)

            for i in range(0, object_count):
                name_length, = struct.unpack("<H", f.read(2))
                anchor_name = f.read(name_length).decode("ascii")
                print("Anchor point %i: %s" % (i, anchor_name))
                m = read_matrix(f)
                self.anchor_points.append((anchor_name, m))
            print("# End list of anchor points", "0x%x" % f.tell())
            f.read(2)  # always 0
            print("# random garbage? ", "0x%x" % f.tell())
            # unk = struct.unpack("f"*12, f.read(48))
            read_material(f)
            f.read(2)  # always 0
            meta1_offset = f.tell()
            meta1 = read_material(f)
            if dump:
                self.material = meta1
            manifest[u'material'] = []
            manifest[u'material'].append(({u'offset': meta1_offset}, meta1))
            print("# Unknown float", struct.unpack("f", f.read(4)))
            print("# End unknown", "0x%x" % f.tell())
        else:
            length, = struct.unpack("<xxH", f.read(4))
            self.parent_name = f.read(length).decode("ascii")
            print("# parent name:", self.parent_name, hex(f.tell()))
            read_material(f)
            read_material(f)
            memory_point_count, = struct.unpack("<I", f.read(4))
            print("# Memory point count", memory_point_count)
            for i in range(0, memory_point_count):
                length, = struct.unpack("<H", f.read(2))
                anchor_name = f.read(length).decode("ascii")
                print("# Memory point name:", anchor_name)
                if length != 0:
                    m = read_matrix(f)
                self.anchor_points.append((anchor_name, m))
                print("#End of sub-meta", "0x%x" % f.tell())
            # possible material info?
            unk = []
            for i in range(int(0x68 / 4)):
                unk.append(*struct.unpack("f", f.read(4)))
                print("0x%x %f" % (f.tell()-4, unk[-1]))
            print("Alpha %f" % unk[-1])
            self.material = {}
            self.material["alpha_constant"] = unk[-1]
            print("# Unknown meta finished", "0x%x" % f.tell())

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

        print("# Start unknown section of 176 bytes", "0x%x" % f.tell())
        for i in range(0, int(0xB0 / 4)):
            unk, = struct.unpack("f", f.read(4))
            if verbose:
                print("# [%i] %i" % (i, unk))
        print("# Finished unknown section", "0x%x" % f.tell())

        ###############################################
        print("# Start vertices")
        vertex_floats, = struct.unpack("<I", f.read(4))
        print("# Vertex count:", vertex_floats / 3)
        manifest[u'vertex_offset'] = f.tell()

        for i in range(0, int(vertex_floats / 3)):
            if not dump:
                f.read(12)
            else:
                x, y, z = struct.unpack("fff", f.read(12))
                self.vertex_array.append((x, y, z))
        print("# End vertices", "0x%x" % f.tell())
        ###############################################

        print("# Start vertex normals")
        normal_count, = struct.unpack("<I", f.read(4))
        print("# Normals count:", normal_count / 3)  # 3 per vertex
        manifest[u'vertex_normals_offset'] = f.tell()

        for i in range(0, int(normal_count / 3)):
            if not dump:
                f.read(6)
            else:
                nx, ny, nz = struct.unpack("<HHH", f.read(6))
                if verbose:
                    print("# [%i] %i %i %i" % (i, nx, ny, nz))
                self.vertex_normal_array.append((nx, ny, nz))
        print("# End normals", "0x%x" % f.tell())
        ###############################################

        unk, = struct.unpack("<I", f.read(4))
        print("# Parsing footer, count:", unk)
        if unk != 0:
            print(f.name)
            for i in range(0, unk):
                print(struct.unpack("<fff", f.read(12)))
                length, = struct.unpack("<I", f.read(4))
                f.read(length * 4)
        print("# End model ##############################################################")
        f.read(1)

        return manifest
