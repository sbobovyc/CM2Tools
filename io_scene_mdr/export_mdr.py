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
from .mdr import MDR, MDRObject


def save(context, filepath, path_mode='AUTO'):
    print("Exporting", filepath, path_mode)
    base_name = os.path.splitext(os.path.basename(filepath))[0]
    m = MDR(filepath, base_name, False, False, False)
    # loop through all selected objects and find one that does not have a parent (ie the root object)
    root_ob = None
    for ob in bpy.context.selected_objects:
        if ob.parent is None:
            root_ob = ob
            break
    ob_list = [root_ob] + list(root_ob.children)

    for ob in ob_list:
        print(ob.name, ob.type, ob.parent)
        if ob.type == 'EMPTY':
            print(ob.matrix_world)
        if ob.type == 'MESH':
            mdr_obj = MDRObject()
            mdr_obj.name = ob.name.encode('ascii')
            mdr_obj.index_array = None

            index_array = []
            me = ob.data
            for f in me.polygons:
                index_array.append((f.vertices[0], f.vertices[1], f.vertices[2]))

            uv_layer = me.uv_layers.active.data  #TODO check to see if this exists

            uv_array = [None] * len(me.vertices)
            mdr_obj.uv_array = uv_array
            vertex_array = []
            vertex_normal_array = []
            for vert in me.vertices:
                # uv_array.append((uv_layer[vert.index].uv[0], uv_layer[vert.index].uv[1]))
                vertex_array.append((vert.co[0], vert.co[1], vert.co[2]))
                vertex_normal_array.append((vert.normal[0], vert.normal[1], vert.normal[2]))

            print("Printing loop uv")
            for i, (face, blen_poly) in enumerate(zip(index_array, me.polygons)):
                blen_uvs = me.uv_layers[0]
                for face_uvidx, lidx in zip(face, blen_poly.loop_indices):
                    print(face_uvidx, lidx, blen_uvs.data[lidx], mdr_obj.uv_array)
                    mdr_obj.uv_array[face_uvidx] = blen_uvs.data[0 if (lidx is ...) else lidx].uv

            diffuse_texture = None
            if me.materials[0].texture_slots[0] is None:
                raise Exception("Missing a diffuse texture")
            else:
                diffuse_texture = me.materials[0].texture_slots[0].texture.image.name

            # strip extension from filenames
            diffuse_texture_file = os.path.splitext(os.path.splitext(diffuse_texture)[0])[0]

            mdr_obj.index_array = index_array
            mdr_obj.uv_array = uv_array
            mdr_obj.vertex_array = vertex_array
            mdr_obj.vertex_normal_array = vertex_normal_array
            mdr_obj.texture_name = diffuse_texture_file.encode('ascii')
            mdr_obj.material["alpha_constant"] = ob.material_slots[0].material.alpha

            m.objects.append(mdr_obj)

    m.write(filepath)

    return {'FINISHED'}