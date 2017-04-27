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
import math
from bpy_extras.io_utils import unpack_list
from bpy_extras.image_utils import load_image
from mathutils import Matrix
from .mdr import MDR


def load(context, use_shadeless, use_smooth_shading, use_transform, use_recursive_search, filepath):
    print(filepath)
    base_name = os.path.splitext(os.path.basename(filepath))[0]
    outdir = ""
    m = MDR(filepath, base_name, False, False, False)
    m.read(outdir)

    new_objects = []  # put new objects here

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

        me.uv_textures.new()
        blen_uvs = me.uv_layers[0]
        for f in me.polygons:
            if use_smooth_shading:
                f.use_smooth = True
            for li in f.loop_indices:
                vi = me.loops[li].vertex_index
                blen_uvs.data[li].uv = mdr_ob.uv_array[vi]
        
        # TODO optimize material creation
        mat = bpy.data.materials.new(me.name)
        mat.specular_shader = 'PHONG'
        mat.diffuse_intensity = 1.0
        mat.specular_intensity = 1.0
        mat.use_transparency = True
        mat.transparency_method = "Z_TRANSPARENCY"
        mat.alpha = 0.0
        tex = bpy.data.textures.new('DiffuseTex', type='IMAGE')
        print("Load diffuse texture", mdr_ob.texture_name)
        img_found = False
        for im in bpy.data.images:
            if im.name == mdr_ob.texture_name+".bmp":
                image = im
                img_found = True
        if not img_found:
            image = load_image(mdr_ob.texture_name+".bmp", os.path.dirname(filepath))
            # if texture file is not found, recursively scan parent dir
            if image is None and use_recursive_search:
                parent_dir = os.path.dirname(os.path.dirname(filepath))
                image = load_image(mdr_ob.texture_name+".bmp", parent_dir, recursive=True)

        if image is not None:
            tex.image = image
        else:
            print("Could not load", mdr_ob.texture_name)
            mat.use_transparency = False

        mtex = mat.texture_slots.add()
        mtex.texture = tex
        mtex.texture_coords = 'UV'
        mtex.use_map_color_diffuse = True
        mtex.use_map_alpha = True
        print(mdr_ob.material)
        if "diffuse_color" in mdr_ob.material:
            mat.diffuse_color = mdr_ob.material["diffuse_color"]
        if "specular_color" in mdr_ob.material:
            mat.specular_color = mdr_ob.material["specular_color"]
        if "alpha_constant" in mdr_ob.material:
            alpha_const = mdr_ob.material["alpha_constant"]
        else:
            alpha_const = 1.0
        if "shininess" in mdr_ob.material:
            mat.specular_hardness = (mdr_ob.material["shininess"]/128.0) * 511.0  # 511 is max hardness in Blender phong shader
        else:
            mat.specular_hardness = 511.0
        print("Alpha const", alpha_const)
        mtex.alpha_factor = alpha_const

        norm_tex_name = mdr_ob.texture_name + "_normal map.bmp"
        norm_tex_path = os.path.join(os.path.dirname(filepath), norm_tex_name)
        print("Looking for", norm_tex_path)
        if os.path.isfile(norm_tex_path):
                print("Load normal texture", norm_tex_name)
                norm_tex = bpy.data.textures.new('NormalTex', type='IMAGE')
                img_found = False
                for im in bpy.data.images:
                    if im.name == norm_tex_name:
                        image = im
                        img_found = True
                if not img_found:
                    image = load_image(norm_tex_name, os.path.dirname(filepath))
                #TODO recursively scan for normal texture
                norm_tex.image = image
                norm_tex.use_normal_map = True
                mnorm = mat.texture_slots.add()
                mnorm.texture = norm_tex
                mnorm.texture_coords = 'UV'
                mnorm.use_map_color_diffuse = False
                mnorm.use_map_normal = True
                mnorm.normal_factor = 5

        if use_shadeless:
            mat.use_shadeless = True

        ob = bpy.data.objects.new(me.name, me)
        ob.data.materials.append(mat)
        new_objects.append(ob)

    for ob, mdr_ob in zip(new_objects, m.objects):
        # parent objects
        if ob != new_objects[0]:
            parent = next((x for x in new_objects if x.name == mdr_ob.parent_name))
            ob.parent = parent
            ob.matrix_parent_inverse = parent.matrix_world.inverted()  # http://blender.stackexchange.com/questions/9200/make-object-a-a-parent-of-object-b-via-python
        #TODO multiply normals by transpose of the inverse of the transform_matrix
        #http://www.scratchapixel.com/lessons/mathematics-physics-for-computer-graphics/geometry/transforming-normals
        if use_transform:
            print("Translating", ob.name)
            forward_matrix = mdr_ob.matrix_array[0]
            backward_matrix = mdr_ob.matrix_array[1]
            m = Matrix(backward_matrix)
            print(m)
            ob.data.transform(m)

            m = Matrix(forward_matrix)
            ob.matrix_world = m

            for v in ob.data.vertices:
                n = v.normal
                v.normal = m.inverted().transposed() * n

        for anchor in mdr_ob.anchor_points:
            print(anchor)
            name = anchor[0]
            matrix = anchor[1]
            m = Matrix(matrix)
            print(m)

            anchor_ob = bpy.data.objects.new(name, None)
            bpy.context.scene.objects.link(anchor_ob)
            anchor_ob.empty_draw_size = 0.1
            anchor_ob.empty_draw_type = 'SINGLE_ARROW'
            anchor_ob.matrix_world = m
            anchor_ob.matrix_local *= Matrix.Rotation(math.radians(90), 4, "Y")

            print(ob, anchor_ob)
            anchor_ob.parent = ob
            anchor_ob.matrix_parent_inverse = ob.matrix_world.inverted()

        context.scene.objects.link(ob)
    return {'FINISHED'}
