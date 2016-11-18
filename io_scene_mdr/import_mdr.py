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
This script imports a Combat Mssion MDR files to Blender.

Usage:
Run this script from "File->Import" menu and then load the desired MDR file.
"""
import bpy
import os
from bpy_extras.io_utils import unpack_list
from .mdr import MDR


def load(context, filepath):
    print(filepath)
    base_name = os.path.splitext(os.path.basename(filepath))[0]
    outdir = ""
    m = MDR(filepath, base_name, outdir, False, False, False)

    new_objects = [] # put new objects here

    for mdr_ob in m.objects:
        print(mdr_ob.name)
        verts_loc = mdr_ob.vertex_array
        faces = mdr_ob.index_array
        me = bpy.data.meshes.new(mdr_ob.name)

        me.vertices.add(len(verts_loc))
        me.loops.add(len(faces)*3)
        me.polygons.add(len(faces))

        # verts_loc is a list of (x, y, z) tuples
        me.vertices.foreach_set("co", unpack_list(verts_loc))
        loops_vert_idx = []
        faces_loop_start = []
        faces_loop_total = []
        lidx = 0
        for f in faces:
            vidx = list(f)
            nbr_vidx = len(vidx)
            loops_vert_idx.extend(vidx)
            faces_loop_start.append(lidx)
            faces_loop_total.append(nbr_vidx)
            lidx += nbr_vidx

        me.loops.foreach_set("vertex_index", loops_vert_idx)
        me.polygons.foreach_set("loop_start", faces_loop_start)
        me.polygons.foreach_set("loop_total", faces_loop_total)

        me.validate(clean_customdata=False)  # *Very* important to not remove lnors here!
        me.update(calc_tessface=True, calc_edges=True)

        ob = bpy.data.objects.new(me.name, me)
        new_objects.append(ob)

    for ob,mdr_ob in zip(new_objects, m.objects):
        # parent objects
        if ob != new_objects[0]:
            parent = next((x for x in new_objects if x.name == mdr_ob.parent_name))
            ob.parent = parent
        context.scene.objects.link(ob)
    return {'FINISHED'}
