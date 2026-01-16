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
import numpy as np
from bpy_extras import node_shader_utils
from bpy_extras.io_utils import unpack_list
from bpy_extras.image_utils import load_image
from mathutils import Matrix, Vector
from .mdr import MDR


def load(context, use_smooth_shading, use_transform, use_materials, use_recursive_search, use_metadata, use_debug, filepath, relpath=None):
    debug_logs = use_debug
    if debug_logs:
        print(filepath)
    base_name = os.path.splitext(os.path.basename(filepath))[0]
    outdir = ""
    m = MDR(filepath, base_name, False, False, debug_logs)
    m.read(outdir)

    new_objects = []  # put new objects here
    new_materials = {}  # put new material object here
    nodal_material_wrap_map = {}

    for mdr_ob in m.objects:
        if debug_logs:
            print("MDR object: ", mdr_ob.name)
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
        me.update(calc_edges=True)

        me.uv_layers.new()
        blen_uvs = me.uv_layers[0]
        for f in me.polygons:
            if use_smooth_shading:
                f.use_smooth = True
            for li in f.loop_indices:
                vi = me.loops[li].vertex_index
                blen_uvs.data[li].uv = mdr_ob.uv_array[vi]

        if use_materials:
            material_name = "%s_%i" % (mdr_ob.texture_name, mdr_ob.material["material_id"])

            if material_name in new_materials:
                if debug_logs:
                    print("Using existing material:", material_name)
                mat = new_materials[material_name]
            else:
                if debug_logs:
                    print("Creating new material:", material_name)
                mat = bpy.data.materials.new(material_name)
                #mat.use_nodes = True
                ma_wrap = node_shader_utils.PrincipledBSDFWrapper(mat, is_readonly=False)
                nodal_material_wrap_map[mat] = ma_wrap

                if debug_logs:
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
                        image = load_image(mdr_ob.texture_name+".bmp", parent_dir, recursive=True, relpath=relpath)

                if image is not None:
                    print(f"{mdr_ob.texture_name=} {image.channels=}")
                    ma_wrap.base_color_texture.image = image
                else:
                    print("Could not load", mdr_ob.texture_name)

                # mtex.texture = tex
                # mtex.texture_coords = 'UV'
                # mtex.use_map_color_diffuse = True
                # mtex.use_map_alpha = True
                print(mdr_ob.material)
                if "diffuse_color" in mdr_ob.material:
                     ma_wrap.base_color = mdr_ob.material["diffuse_color"]
                if "specular_color" in mdr_ob.material:
                     # PrincipalBSDF does not have specular color. Game does not seem to use different values for each color channel,
                     # so using similar approach to Wavefront OBJ plugin. Take average and store in specular IOR level.
                     ma_wrap.specular = sum(mdr_ob.material["specular_color"]) / 3.0
                if "alpha_constant" in mdr_ob.material:
                     alpha_const = mdr_ob.material["alpha_constant"]
                else:
                     alpha_const = 1.0
                if "shininess" in mdr_ob.material:
                     # Mapping MDR shininess to BSDF roughness
                     print("Calcularing shinines %f" % mdr_ob.material["shininess"])
                     ma_wrap.roughness = np.clip(1.0 - math.sqrt((mdr_ob.material["shininess"]*0.3)/128.0), 0.0, 1.0)
                     print("Calculated roughness %f" % ma_wrap.roughness)
                else:
                     ma_wrap.roughness = 1.0

                ma_wrap.ior = 1.0 # default all materials to not use Fresnel effect
                # alpha constant is used by Blender BSDF if there is not an alpha image source
                ma_wrap.alpha = alpha_const

                if image is not None and (alpha_const < 1.0 or image.depth == 32):
                        print("Attempting to add alpha texture %s, channels %i" % (image.name, image.channels))
                        ma_wrap.alpha_texture.image = image
                        mat.blend_method = 'BLEND'
                        #TODO this is a bit of a hack to get around textures that use 1 bit alpha
                        mat.show_transparent_back = False

                        # add multiply node between alpha texture and BSDF alpha input
                        bsdf_node = mat.node_tree.nodes.get("Principled BSDF")  # actual Principled BSDF node
                        nodes = mat.node_tree.nodes
                        links = mat.node_tree.links

                        # Find an image texture node that feeds alpha
                        image_node = None
                        alpha_link = None

                        # actual 32 bit BMP image will feed from alpha to alpha
                        for link in links:
                            if (link.to_node == bsdf_node and
                                link.to_socket.name == "Alpha" and
                                link.from_socket.name == "Alpha"):
                                image_node = link.from_node
                                alpha_link = link
                                break
                        # however, 24 bit BMP image will feed from color to alpha which is not desired, so delete that link
                        if not image_node:
                            for link in links:
                                if (link.to_node == bsdf_node and
                                    link.to_socket.name == "Alpha" and
                                    link.from_socket.name == "Color"):
                                    image_node = link.from_node
                                    links.remove(link)
                                    break
                        if not image_node:
                            print("No image texture feeding BSDF Alpha")
                        else:
                            # Create Math node
                            math_node = nodes.new(type='ShaderNodeMath')
                            math_node.operation = 'MULTIPLY'
                            math_node.use_clamp = True
                            math_node.inputs[1].default_value = alpha_const

                            # Place it visually
                            math_node.location = (
                                (image_node.location.x + bsdf_node.location.x) / 2,
                                image_node.location.y + 320
                            )
                            # move image node for a cleaner look
                            image_node.location = (image_node.location.x - 100, image_node.location.y)

                            # Rewire
                            if alpha_link:
                                links.remove(alpha_link)
                            links.new(image_node.outputs["Alpha"], math_node.inputs[0])
                            links.new(math_node.outputs["Value"], bsdf_node.inputs["Alpha"])

                norm_tex_name = mdr_ob.texture_name + "_normal map.bmp"
                norm_tex_path = os.path.join(os.path.dirname(filepath), norm_tex_name)
                print("Looking for", norm_tex_path)
                if os.path.isfile(norm_tex_path):
                         print("Load normal texture", norm_tex_name)
                #         norm_tex = bpy.data.textures.new('NormalTex', type='IMAGE')
                         img_found = False
                         for im in bpy.data.images:
                             if im.name == norm_tex_name:
                                 image = im
                                 img_found = True
                         if not img_found:
                             image = load_image(norm_tex_name, os.path.dirname(filepath))
                         #TODO recursively scan for normal texture
                #         norm_tex.image = image
                #         norm_tex.use_normal_map = True
                #         mnorm = mat.texture_slots.add()
                #         mnorm.texture = norm_tex
                #         mnorm.texture_coords = 'UV'
                #         mnorm.use_map_color_diffuse = False
                #         mnorm.use_map_normal = True
                #         mnorm.normal_factor = 1.0
                         ma_wrap.normalmap_texture.image = image
                new_materials[material_name] = mat

        ob = bpy.data.objects.new(me.name, me)
        if debug_logs:
            print("Created Blender object", ob.name)
        if use_materials:
            print("Transparent back", mat.name, mat.show_transparent_back)
            ob.data.materials.append(mat)
        new_objects.append(ob)

    for ob, mdr_ob in zip(new_objects, m.objects):
        # parent objects
        if ob != new_objects[0]:
            # Blender does not allow objects with the same names, so have to remove postfix to find correct parent
            demangled_parent_name = mdr_ob.parent_name.split('.')[0]
            parent = next((x for x in new_objects if x.name.split('.')[0] == demangled_parent_name))
            ob.parent = parent
            ob.matrix_parent_inverse = parent.matrix_world.inverted()  # http://blender.stackexchange.com/questions/9200/make-object-a-a-parent-of-object-b-via-python
        #http://www.scratchapixel.com/lessons/mathematics-physics-for-computer-graphics/geometry/transforming-normals
        transform_matrix = Matrix(mdr_ob.transform_matrix)
        inverse_transform_matrix = Matrix(mdr_ob.inverse_transform_matrix)

        if use_transform:
            if debug_logs:
                print("Translating", ob.name)

            # in some cases, object transform is not used
            if np.sum(np.abs(transform_matrix.inverted() - inverse_transform_matrix)) < 0.01:
                if debug_logs:
                    print("Transform matrix:")
                    print(transform_matrix)
                    print("Inverse transform matrix:")
                    print(inverse_transform_matrix)

                ob.data.transform(inverse_transform_matrix)

                if inverse_transform_matrix.determinant() < 0:
                    print("Warning: inverse_transform_matrix will invert normals, so flipping normals")
                    for poly in ob.data.polygons:
                        poly.flip()

                ob.matrix_world = transform_matrix
            else:
                print("Transform mismatch!")
                if debug_logs:
                    print("Transform matrix:")
                    print(transform_matrix)
                    print("Transform matrix inverted:")
                    print(transform_matrix.inverted())
                    print("Inverse transform matrix:")
                    print(inverse_transform_matrix)
                    print("Inverse transform matrix inverted:")
                    print(inverse_transform_matrix.inverted())
                    print("Transform matrix - inverse transform matrix inverted:")
                    print(transform_matrix - inverse_transform_matrix.inverted())

        # print out Blender bounding box
        if debug_logs:
            coords = [ob.matrix_world @ Vector(corner) for corner in ob.bound_box]

            min_corner = Vector((
                min(v.x for v in coords),
                min(v.y for v in coords),
                min(v.z for v in coords),
            ))

            max_corner = Vector((
                max(v.x for v in coords),
                max(v.y for v in coords),
                max(v.z for v in coords),
            ))

            print(f"Blender bounding box min {ob.name}: {min_corner}")
            print(f"Blender bounding box max {ob.name}: {max_corner}")
            # calculate bounding box center
            local_center = sum((Vector(corner) for corner in ob.bound_box), Vector()) / 8
            world_center = ob.matrix_world @ local_center
            print(f"Blender bounding box local center {ob.name}: {local_center}")
            print(f"Blender bounding box world center {ob.name}: {world_center}")

            min_bbox = Vector((mdr_ob.bbox_x_min, mdr_ob.bbox_y_min, mdr_ob.bbox_z_min))
            max_bbox = Vector((mdr_ob.bbox_x_max, mdr_ob.bbox_y_max, mdr_ob.bbox_z_max))
            print(f"MDR bounding box min {ob.name}: {min_bbox}")
            print(f"MDR bounding box max {ob.name}: {max_bbox}")
            bbox_center = (Vector(min_bbox) + Vector(max_bbox)) / 2
            print(f"MDR bounding box center {ob.name}: {bbox_center}")
            #print(transform_matrix @ min_bbox)
            #print(transform_matrix @ max_bbox)
            #print(inverse_transform_matrix @ min_bbox)
            #print(inverse_transform_matrix @ max_bbox)


        view_layer = bpy.context.view_layer
        collection = view_layer.active_layer_collection.collection

        for anchor in mdr_ob.anchor_points:
            if debug_logs:
                print(anchor)
            name = anchor[0]
            matrix = anchor[1]
            m = Matrix(matrix)
            if debug_logs:
                print("Anchor matrix:")
                print(m)

            anchor_ob = bpy.data.objects.new(name, None)
            collection.objects.link(anchor_ob)
            anchor_ob.empty_display_size = 0.1
            anchor_ob.empty_display_type = 'SINGLE_ARROW'
            anchor_ob.matrix_world = m
            anchor_ob.matrix_local = anchor_ob.matrix_local @ Matrix.Rotation(math.radians(90), 4, "Y")

            if debug_logs:
                print(ob, anchor_ob)
            anchor_ob.parent = ob
            anchor_ob.matrix_parent_inverse = ob.matrix_world.inverted()

        # metadata
        if use_metadata:
            for i in range(0, len(mdr_ob.meta_data1)):
                ob["meta1_%i" % i] = mdr_ob.meta_data1[i]
            for i in range(0, len(mdr_ob.meta_data2)):
                ob["meta2_%i" % i] = mdr_ob.meta_data2[i]
            for i in range(0, len(mdr_ob.meta_data3)):
                ob["meta3_%i" % i] = mdr_ob.meta_data3[i]
            ob["meta_unk1"] = mdr_ob.meta_data_unk1
            ob["meta_unk2"] = mdr_ob.meta_data_unk2
            for meta in mdr_ob.foliage_meta:
                ob["foliage_meta_%s" % meta] = mdr_ob.foliage_meta[meta]
        collection.objects.link(ob)
        view_layer.update()
    return {'FINISHED'}
