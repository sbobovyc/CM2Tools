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
                print(index_array)

            uv_layer = me.uv_layers.active.data
            for poly in me.polygons:
                print("Polygon", poly.index)
                for li in poly.loop_indices:
                    vi = me.loops[li].vertex_index
                    uv = uv_layer[li].uv
                    print("Loop index %i (Vertex %i) - UV %f %f" % (li, vi, uv.x, uv.y))

            uv_array = []

            mdr_obj.index_array = index_array

            m.objects.append(mdr_obj)

    m.write(filepath)

    return {'FINISHED'}