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

import numpy as np
import struct
import logging
import io

def read_matrix(f: io.BufferedIOBase) -> np.ndarray:
    logging.info("Start reading matrix 0x%x", f.tell())
    mat = np.identity(4)

    # 3x4 matrix, column order
    for column in range(0, 4):
        for row in range(0, 3):
            value, = struct.unpack("f", f.read(4))
            logging.debug("0x%x [%i] %f", f.tell() - 4, column, value)
            mat[row][column] = value
    logging.info("This is a transform matrix:")
    logging.info(f"\n{mat}")
    return mat


def write_matrix(mat: np.ndarray, f: io.BufferedIOBase) -> None:
    # 3x4 matrix, column order
    for column in range(0, 4):
        f.write(struct.pack("fff", *mat[column][:3]))


def read_material(f: io.BufferedIOBase) -> dict:
    logging.info("Start reading material 0x%x", f.tell())
    ambient_color = struct.unpack("fff", f.read(4 * 3))
    if ambient_color[0] != ambient_color[1] or ambient_color[1] != ambient_color[2]:
        logging.error("Ambient color elements differ!")
    logging.info("Ambient color %s", ambient_color)  # GL_AMBIENT
    diffuse_color = struct.unpack("fff", f.read(4 * 3))
    if diffuse_color[0] != diffuse_color[1] or diffuse_color[1] != diffuse_color[2]:
        logging.error("Diffuse color elements differ!")
    logging.info("Diffuse color %s", diffuse_color)  # GL_DIFFUSE
    specular_color = struct.unpack("fff", f.read(4 * 3))
    if specular_color[0] != specular_color[1] or specular_color[1] != specular_color[2]:
        logging.error("Specular color elements differ!")
    logging.info("Specular color %s", specular_color)  # GL_SPECULAR
    shininess, = struct.unpack("f", f.read(4))
    logging.info("Shininess %f", shininess)  # GL_SHININESS
    alpha_constant, = struct.unpack("f", f.read(4))
    logging.info("Alpha constant %f", alpha_constant)
    material_id, = struct.unpack("<I", f.read(4))
    logging.info("Material id %i", material_id)  # saved at 005CE8A6
    logging.info("End material 0x%x", f.tell())

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
            self.num_models, = struct.unpack("<I", f.read(4))  # read from 008A04D8
            logging.info(f"number of models {self.num_models}")
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
                #TODO write out foliage_meta
                if len(o.meta_data1) != 0:
                    for i in range(0, 11):
                        f.write(struct.pack("f", o.meta_data1[i]))
                    if len(o.meta_data2) != 0:
                        for i in range(0, 24):
                            logging.info("writing %f", o.meta_data2[i])
                            f.write(struct.pack("f", o.meta_data2[i]))
                        # f.write(struct.pack('x' * 12))
                        f.write(struct.pack("fff", *o.meta_data_unk1))
                    else:
                        f.write(struct.pack('x' * 108))
                else:
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
                if len(o.meta_data3) != 0:
                    for i in range(0, 35):
                        f.write(struct.pack("f", o.meta_data3[i]))
                    # f.write(struct.pack('x' * 12))
                    f.write(struct.pack("fff", *o.meta_data_unk2))
                else:
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
        self.bbox_x_min = 0.0
        self.bbox_x_max = 0.0
        self.bbox_y_min = 0.0
        self.bbox_y_max = 0.0
        self.bbox_z_min = 0.0
        self.bbox_z_max = 0.0
        self.transform_matrix = None
        self.inverse_transform_matrix = None
        self.foliage_meta = {}

        # all the WIP data
        self.uint8_unk0 = None
        self.meta_data1 = []
        self.meta_data2 = []
        self.meta_data3 = []
        self.meta_data_unk1 = None
        self.meta_data_unk2 = None

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
        logging.info("#"*50)
        logging.info(f"Start model {model_number} at {f.tell():#x}")
        f.read(1)
        name_length, = struct.unpack("<H", f.read(2))
        logging.info(f"submodel name length: {name_length}")
        self.name = f.read(name_length).decode("ascii")
        logging.info(f"submodel name: {self.name}")

        logging.info("Start collision metadata")
        # read one byte, but it is saved as 4 byte in memory
        self.uint8_unk0, = struct.unpack("b", f.read(1))
        logging.info(f"{self.uint8_unk0=} at {f.tell() - 1:#x}")
        if self.uint8_unk0 != 2:
            error_message = "self.uint8_unk0 is %s, not 2, 0x%x %s, %s, %s" % (
            self.uint8_unk0, f.tell() - 1, base_name, self.name, model_number)
            print(error_message)
            logging.error(error_message)


        logging.info(f"Start unknown section of 176 bytes, has something to do with collision box at {f.tell():#x}")

        for i in range(0, 11):
            unk, = struct.unpack("f", f.read(4))
            self.meta_data1.append(unk)
            logging.debug("meta_data1 0x%x [%i] %f", f.tell() - 4, i, unk)

        logging.debug("################")

        # this is read in a separate loop from meta_data1
        for i in range(0, 6):
            for j in range(0, 4):
                unk, = struct.unpack("f", f.read(4))
                self.meta_data2.append(unk)
                logging.debug("meta_data2 0x%x [%i] %f", f.tell() - 4, i, unk)
        logging.debug("################")

        unk = struct.unpack("fff", f.read(12))
        self.meta_data_unk1 = unk
        logging.info(f"{self.meta_data_unk1=} at {f.tell() - 12:#x}")  # saved separate from bbox
        self.bbox_x_min, self.bbox_x_max, self.bbox_y_min, self.bbox_y_max, self.bbox_z_min, self.bbox_z_max = struct.unpack("ffffff", f.read(24))
        logging.info("Bound box min/max")
        logging.info(f"xmin {self.bbox_x_min}")
        logging.info(f"xmax {self.bbox_x_max}")
        logging.info(f"ymin {self.bbox_y_min}")
        logging.info(f"ymax {self.bbox_y_max}")
        logging.info(f"zmin {self.bbox_z_min}")
        logging.info(f"zmax {self.bbox_z_max}")
        logging.info(f"Finished unknown section {f.tell():#x}")

        ###############################################
        logging.info(f"Start face vertex indices at {f.tell():#x}")
        face_count, = struct.unpack("<I", f.read(4))
        logging.info(f"Face count: {int(face_count / 3)}")

        for i in range(0, int(face_count / 3)):
            if not dump:
                f.read(6)
            else:
                v0, v1, v2 = struct.unpack("<HHH", f.read(6))
                self.index_array.append((v0, v1, v2))
        logging.info(f"Finished face vertex indices {f.tell():#x}")
        ###############################################

        ###############################################
        logging.info(f"Start UVs at {f.tell():#x}")
        uv_in_section, = struct.unpack("<I", f.read(4))
        logging.info(f"UV in section: {int(uv_in_section / 2)}")

        for i in range(0, int(uv_in_section / 2)):  # read at 00453965
            if not dump:
                f.read(8)
            else:
                u, v = struct.unpack("<ff", f.read(8))
                self.uv_array.append((u, v))
        logging.info(f"Finish UV section: {f.tell():#x}")
        ###############################################

        logging.info("Start unknown section 1")
        uv_last_index, = struct.unpack("<I", f.read(4))
        logging.info(f"{uv_last_index=} at {f.tell() - 4:#x}")  # saved in a different function from UV, right after UV data
        if uv_last_index != uv_in_section/2 - 1:
            logging.error("Last uv index != uv_in_section/2 - 1")

        foliage_meta_count, = struct.unpack("<H", f.read(2))  # used by CMSF2 for foliage metadata
        logging.info(f"{foliage_meta_count=} at {f.tell() - 4:#x}")
        if foliage_meta_count != 0:
            logging.info("################")
            for i in range(0, foliage_meta_count):
                length, = struct.unpack("<H", f.read(2))
                meta_name = f.read(length).decode("ascii")
                meta_count, = struct.unpack("<H", f.read(2))
                meta_data = struct.unpack('b'*meta_count, f.read(meta_count))
                logging.info(f"foliage_meta: {meta_name} {meta_data}")
                self.foliage_meta[meta_name] = meta_data
            logging.info("################")

        length, = struct.unpack("<H", f.read(2))
        self.parent_name = ""
        if length > 0:
            self.parent_name = f.read(length).decode("ascii")
            logging.info(f"{self.name=}, {self.parent_name=} at {f.tell():#x}")

        logging.info("Reading object transform matrix")
        self.transform_matrix = read_matrix(f)  # read at 004532C1
        logging.info("Reading object inverse transform matrix")
        self.inverse_transform_matrix = read_matrix(f)  # read at 004532D1

        anchor_point_count, = struct.unpack("<I", f.read(4))
        logging.info(f"{anchor_point_count=}")

        for i in range(0, anchor_point_count):
            name_length, = struct.unpack("<H", f.read(2))
            anchor_name = f.read(name_length).decode("ascii")
            logging.info(f"Anchor point {i}: {anchor_name}")
            m = read_matrix(f)
            self.anchor_points.append((anchor_name, m))
        logging.info(f"End list of anchor points at {f.tell():#x}")

        logging.info(f"Start unknown data at {f.tell():#x}")
        #TODO log this
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

        logging.info(f"End unknown data at {f.tell():#x}")

        self.material = read_material(f)

        name_length, = struct.unpack("<H", f.read(2))  # read length of string
        texture_name = f.read(name_length).decode("ascii")
        logging.info(f"Texture name: {texture_name}")

        if dump:
            self.texture_name = texture_name

        unk3, = struct.unpack("b", f.read(1))  # read at 00453462
        if unk3 != 2:
            error_message = error_message = "unk3 is %s, not 2, 0x%x %s, %s, %s" % (
            unk3, f.tell() - 1, base_name, self.name, model_number)
            # raise ValueError(error_message)
            logging.info(error_message)
        else:
            logging.info("unk3 is %s (always 2?) 0x%x %s, %s, %s", unk3, f.tell() - 1, base_name, self.name, model_number)
        # read 4, 11 starting at 0045347B
        logging.info(f"Start unknown section of 176 bytes, has something to do with collision box at {f.tell():#x}")
        for i in range(0, 35):
            unk, = struct.unpack("f", f.read(4))
            self.meta_data3.append(unk)
            logging.debug("meta_data3 0x%x [%i] %f", f.tell() - 4, i, unk)

        self.meta_data_unk2 = struct.unpack("fff", f.read(12))
        logging.info(f"{self.meta_data_unk2=} at {f.tell() - 12:#x}")  # read at different place than meta_data_unk1
        self.bbox_x_min, self.bbox_x_max, self.bbox_y_min, self.bbox_y_max, self.bbox_z_min, self.bbox_z_max = struct.unpack("ffffff", f.read(24))
        logging.info("Bound box min/max")
        logging.info(f"xmin {self.bbox_x_min}")
        logging.info(f"xmax {self.bbox_x_max}")
        logging.info(f"ymin {self.bbox_y_min}")
        logging.info(f"ymax {self.bbox_y_max}")
        logging.info(f"zmin {self.bbox_z_min}")
        logging.info(f"zmax {self.bbox_z_max}")
        logging.info(f"Finished unknown section {f.tell():#x}")

        logging.info(f"Start vertices at {f.tell():#x}")
        vertex_floats, = struct.unpack("<I", f.read(4))
        logging.info(f"Vertex count: {int(vertex_floats / 3)}")

        for i in range(0, int(vertex_floats / 3)):
            if not dump:
                f.read(12)
            else:
                x, y, z = struct.unpack("fff", f.read(12))
                self.vertex_array.append((x, y, z))
        logging.info(f"End vertices at {f.tell():#x}")

        logging.info(f"Start vertex normals at {f.tell():#x}")
        normal_count, = struct.unpack("<I", f.read(4))
        logging.info(f"Normals count: {int(normal_count / 3)}")  # 3 per vertex

        for i in range(0, int(normal_count / 3)):  # read at 00453727
            if not dump:
                f.read(6)
            else:
                nx, ny, nz = struct.unpack("<hhh", f.read(6))
                self.vertex_normal_array.append((nx, ny, nz))
        logging.info(f"End normals at {f.tell():#x}")

        footer_counter, = struct.unpack("<I", f.read(4))  # read at 00453649
        logging.info(f"{footer_counter=}")
        if footer_counter != 0:
            logging.info(f"Parsing footer at {f.tell():#x}")
            for i in range(0, footer_counter):
                logging.info(struct.unpack("<fff", f.read(12)))
                length, = struct.unpack("<I", f.read(4))
                logging.info(f"{length=}")
                logging.info(f"Uknown content {f.read(length * 4)}")
        logging.info("End model 0x%x", f.tell())
