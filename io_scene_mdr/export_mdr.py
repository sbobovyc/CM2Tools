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
This script exports from Blender to Combat Mssion MDR files.

Usage:
Run this script from "File->Export" menu.
"""
import bpy
import os
import math
import numpy as np
from pathlib import Path
from mathutils import Matrix, Vector
from bpy_extras import node_shader_utils
from .mdr import MDR, MDRObject


def bounds(obj, local=False):
    local_coords = obj.bound_box[:]
    om = obj.matrix_world

    if not local:
        worldify = lambda p: om @ Vector(p[:])
        coords = [worldify(p).to_tuple() for p in local_coords]
    else:
        coords = [p[:] for p in local_coords]

    rotated = zip(*coords[::-1])

    push_axis = []
    for (axis, _list) in zip('xyz', rotated):
        info = lambda: None
        info.max = max(_list)
        info.min = min(_list)
        info.distance = info.max - info.min
        push_axis.append(info)

    import collections

    originals = dict(zip(['x', 'y', 'z'], push_axis))

    o_details = collections.namedtuple('object_details', 'x y z')
    return o_details(**originals)


def save(operator, context, filepath, var_float=1.0, use_metadata=False, path_mode='AUTO'):
    if len(bpy.context.selected_objects) == 0:
        operator.report({'ERROR'}, "You must select a mesh object to export")
        return {'CANCELLED'}

    print("Exporting", filepath, path_mode)
    base_name = os.path.splitext(os.path.basename(filepath))[0]
    m = MDR(filepath, base_name, False, False, False)
    # loop through all selected objects and find one that does not have a parent (ie the root object)
    root_obj = None
    child_objs = []
    for ob in bpy.context.selected_objects:
        if ob.parent is None:
            root_obj = ob
        else:
            child_objs.append(ob)
    ob_list = [root_obj] + child_objs

    for ob in ob_list:
        print(type(ob), ob.name, ob.type, ob.parent)
        matrix_world = ob.matrix_basis  # world matrix so we can transform from local to global coordinates
        if ob.type == 'MESH':
            mdr_obj = MDRObject()
            mdr_obj.name = ob.name.encode('ascii')
            if ob.parent is not None:
                mdr_obj.parent_name = ob.parent.name.encode('ascii')
            mdr_obj.index_array = None

            for c in ob.children:
                print("Checking children", c, c.type)
                if c.type == 'EMPTY':
                    # print(c.name, c.matrix_world)
                    achor_matrix = c.matrix_world @ Matrix.Rotation(math.radians(-90), 4, "Y")
                    # print(achor_matrix)
                    print(c.name, Matrix.transposed(achor_matrix))
                    mdr_obj.anchor_points.append((c.name.encode('ascii'), Matrix.transposed(achor_matrix)))

            index_array = []
            me = ob.data
            for f in me.polygons:
                index_array.append((f.vertices[0], f.vertices[1], f.vertices[2]))

            if len(me.uv_layers) == 0:
                operator.report({'ERROR'}, "Object %s is missing a texture map" % ob.name)
                return {'CANCELLED'}
            uv_data = me.uv_layers.active.data

            uv_array = [None] * len(me.vertices)
            mdr_obj.uv_array = uv_array
            vertex_array = []
            vertex_normal_array = []
            for vert in me.vertices:
                x, y, z = matrix_world @ vert.co.xyz
                vertex_array.append((x, y, z))
                transformed_normal = matrix_world.inverted().transposed() @ vert.normal
                # normalized transformed normal in case the object was scaled
                nx, ny, nz = transformed_normal.normalized()
                norm = (int(nx * 32767.0), int(ny * 32767.0), int(nz * 32767.0))
                vertex_normal_array.append(norm)

            # for i, (face, blen_poly) in enumerate(zip(index_array, me.polygons)):
            #     blen_uvs = me.uv_layers[0]
            #     for face_uvidx, lidx in zip(face, blen_poly.loop_indices):
            #         # print(face_uvidx, lidx, blen_uvs.data[lidx], mdr_obj.uv_array)
            #         mdr_obj.uv_array[face_uvidx] = blen_uvs.data[0 if (lidx is ...) else lidx].uv
            for poly in me.polygons:
                # print("Polygon", poly.index)
                for li in poly.loop_indices:
                    vi = me.loops[li].vertex_index
                    uv = uv_data[li].uv
                    # print("    Loop index %i (Vertex %i) - UV %f %f" % (li, vi, uv.x, uv.y))
                    mdr_obj.uv_array[vi] = uv
            # for i in range(0, len(mdr_obj.uv_array)):
            #     print(i, mdr_obj.uv_array[i])

            # bound box
            object_bound_box = bounds(ob, False)
            mdr_obj.bbox_x_min = object_bound_box.x.min
            mdr_obj.bbox_x_max = object_bound_box.x.max
            mdr_obj.bbox_y_min = object_bound_box.y.min
            mdr_obj.bbox_y_max = object_bound_box.y.max
            mdr_obj.bbox_z_min = object_bound_box.z.min
            mdr_obj.bbox_z_max = object_bound_box.z.max

            #TODO make variable names consistent with import
            diffuse_texture_wrap = None
            diffuse_texture_file = None
            diffuse_color = None
            specular_color = None
            specular_tint = None
            alpha = None
            print("Number of materials: %s" % len(me.materials))
            #TODO handle cases where texture is missing from material
            if me.materials[0] is None:
                operator.report({'ERROR'}, "%s object material is missing" % ob.name)
                return {'CANCELLED'}
            for material in me.materials:
                print("Material: ", material)
            mat_wrap = node_shader_utils.PrincipledBSDFWrapper(me.materials[0]) if me.materials[0] else None
            if mat_wrap:
                diffuse_texture_wrap = getattr(mat_wrap, "base_color_texture", None)
                print("Got color texture", diffuse_texture_wrap.image.filepath)
                diffuse_texture_file = Path(diffuse_texture_wrap.image.filepath).stem
                diffuse_color = mat_wrap.base_color[:3]
                print("Got diffuse color: %.6f %.6f %.6f" % diffuse_color)
                specular_color = mat_wrap.specular
                print("Got specular color: ", specular_color)
                specular_tint = mat_wrap.specular_tint
                print("Got specular tint: ", specular_tint)
                alpha = mat_wrap.alpha
                print("Got alpha (BSDF): ", alpha)

                # if image alpha is used, find the math multiply node to extract the alpha constant instead of using the BSDF alpha constant
                mat = me.materials[0]
                bsdf_node = mat.node_tree.nodes.get("Principled BSDF")  # actual Principled BSDF node
                nodes = mat.node_tree.nodes
                links = mat.node_tree.links
                math_node = None
                for link in bsdf_node.inputs["Alpha"].links:
                    if link.from_node.type == 'MATH' and link.from_node.operation == 'MULTIPLY':
                        math_node = link.from_node
                        break

                if math_node:
                    if not math_node.inputs[0].is_linked and not math_node.inputs[1].is_linked:
                        operator.report({'ERROR'}, "%s object alpha material input to multiply math node is missing!" % ob.name)
                        return {'CANCELLED'}
                    if math_node.inputs[0].is_linked:
                        alpha = math_node.inputs[1].default_value
                        print(f"Got alpha {math_node.inputs[1].default_value=}")
                    else:
                        alpha = math_node.inputs[0].default_value
                        print(f"Got alpha {math_node.inputs[0].default_value=}")
                elif bsdf_node.inputs["Alpha"].is_linked:
                    operator.report({'ERROR'}, "%s object alpha link exists, but the multiply math node does not!" % ob.name)
                    return {'CANCELLED'}
            else:
                operator.report({'ERROR'}, "%s object material is wrapping failed" % ob.name)
                return {'CANCELLED'}

            #TODO check that all objects are not None

            mdr_obj.index_array = index_array
            mdr_obj.uv_array = uv_array
            mdr_obj.vertex_array = vertex_array
            mdr_obj.vertex_normal_array = vertex_normal_array
            mdr_obj.texture_name = diffuse_texture_file.encode('ascii')
            print(f"Diffuse texture name: {mdr_obj.texture_name}")
            matrix_zero4x4 =  Matrix([(0,0,0,0), (0,0,0,0), (0,0,0,0), (0,0,0,0)])
            mdr_obj.transform_matrix = matrix_world.transposed() + matrix_zero4x4 # Blender stores matrix in row-major, mdr uses column major
            mdr_obj.inverse_transform_matrix = matrix_world.inverted().transposed() + matrix_zero4x4
            mdr_obj.material["diffuse_color"] = tuple(ob.material_slots[0].material.diffuse_color) #TODO which diffuse color to use?
            mdr_obj.material["diffuse_color"] = tuple(diffuse_color)
            mdr_obj.material["specular_color"] = (specular_color,) * 3
            print("specular_color?: ", mdr_obj.material["specular_color"])
            # convert BSDF roughness to GL_SHININESS (with the game's scaling factor taken into account)
            mdr_obj.material["shininess"] = np.clip(((1.0-ob.material_slots[0].material.roughness)**2)*(128.0/0.3), 0.0, 128.0)
            print(f"Calculated shininess: {mdr_obj.material['shininess']}")
            mdr_obj.material["alpha_constant"] = alpha
            for i,key in enumerate(bpy.data.materials.keys()):
                if ob.material_slots[0].material == bpy.data.materials[key]:
                    mdr_obj.material["material_id"] = i

            mdr_obj.meta_data1 = []
            mdr_obj.meta_data2 = []
            mdr_obj.meta_data3 = []
            mdr_obj.foliage_meta = {}
            if use_metadata:
                for i in range(0, 11):
                    try:
                        mdr_obj.meta_data1.append(ob["meta1_%i" % i])
                    except KeyError as e:
                        print(e)
                for i in range(0, 24):
                    try:
                        mdr_obj.meta_data2.append(ob["meta2_%i" % i])
                    except KeyError as e:
                        print(e)
                for i in range(0, 35):
                    try:
                        mdr_obj.meta_data3.append(ob["meta3_%i" % i])
                    except KeyError as e:
                        print(e)
                mdr_obj.meta_data_unk1 = ob["meta_unk1"]
                mdr_obj.meta_data_unk2 = ob["meta_unk2"]
            #TODO export foliage_meta
            print("Exporting %i faces" % len(mdr_obj.index_array))
            print("Exporting %i texture coords" % len(mdr_obj.uv_array))
            print("Exporting %i vertices" % len(mdr_obj.vertex_array))
            mdr_obj.var_float = var_float
            m.objects.append(mdr_obj)

    m.write(filepath)

    return {'FINISHED'}
