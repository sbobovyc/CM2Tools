from __future__ import print_function

"""@package unmdr
Documentation for this module. 
More details.
"""

"""
Copyright (C) 2014 Stanislav Bobovych
This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.
You should have received a copy of the GNU General Public License
along with this program. If not, see <http://www.gnu.org/licenses/>.
"""


import os
import sys
import argparse


sys.path.append("io_scene_mdr") # doing this instead of import to avoid executing __init__.py
from mdr import MDR

def float2string(f):
    return "{0:.12f}".format(f)

def short2float(value):
    return float(value + 2**15) / 2**15 - 1.0

def make_wavefront_obj(mdr_ob):
    """ Serialize mdr to obj format and return it as a string."""
    string = ""
    string += "o %s\n" % mdr_ob.name
    # write material info
    string += "mtllib %s\n" % mdr_ob.name
    string += "usemtl %s\n" % mdr_ob.name

    use_Blender_order = True
    # write vertex info
    if use_Blender_order:
        for vert in mdr_ob.vertex_array:
            string += "v %s %s %s\n" % ( float2string(vert[0]), float2string(vert[1]), float2string(vert[2]))
        for uv in mdr_ob.uv_array:
            string += "vt %s %s\n" % (uv[0], uv[1])
        for norm in mdr_ob.vertex_normal_array:
            string += "vn %s %s %s\n" % (short2float(norm[0]), short2float(norm[1]), short2float(norm[2]))
        for idx in mdr_ob.index_array:
            # string += "f %i/%i/%i %i/%i/%i %i/%i/%i\n" % (
            # idx[0] + 1, idx[0] + 1, idx[0] + 1, idx[1] + 1, idx[1] + 1, idx[1] + 1, idx[2] + 1, idx[2] + 1,
            # idx[2] + 1)
            string += "f %i/%i %i/%i %i/%i\n" % (
            idx[0] + 1, idx[0] + 1, idx[1] + 1, idx[1] + 1, idx[2] + 1, idx[2] + 1)
    else:
        for idx in mdr_ob.index_array:
            string += "f %i/%i/%i %i/%i/%i %i/%i/%i\n" % (
            idx[0] + 1, idx[0] + 1, idx[0] + 1, idx[1] + 1, idx[1] + 1, idx[1] + 1, idx[2] + 1, idx[2] + 1,
            idx[2] + 1)
        for uv in mdr_ob.uv_array:
            string += "vt %s %s\n" % (uv[0], uv[1])
        for vert in mdr_ob.vertex_array:
            string += "v %s %s %s\n" % ( float2string(vert[0]), float2string(vert[1]), float2string(vert[2]))
        for norm in mdr_ob.vertex_normal_array:
            string += "vn %s %s %s\n" % (short2float(norm[0]), short2float(norm[1]), short2float(norm[2]))

    return string


def make_wavefront_mtl(mdr_ob):
    """ Create a material definition file."""
    string = ""
    string += "newmtl %s\n" % mdr_ob.name
    if "ambient_color" not in mdr_ob.material:
        string += "Ka 0.5 0.5 0.5 # gray\n"   # ambient color
        string += "Kd 0.5 0.5 0.5 # gray\n"   # diffuse color
        string += "Ks 0.0 0.0 0.0\n"          # specular color, off
        string += "Ns 0.0\n"                  # specular exponent
    else:
        string += "Ka %f %f %f\n" % (mdr_ob.material["ambient_color"])
        string += "Kd %f %f %f\n" % (mdr_ob.material["diffuse_color"])
        string += "Ks %f %f %f\n" % (mdr_ob.material["specular_color"])
        string += "Ns %f\n" % (mdr_ob.material["specular_exponent"])
    string += "d 1.0\n"                   # transparency
    string += "illum 1\n"                 # Color on and Ambient on
    string += "map_Kd %s.bmp\n" % mdr_ob.texture_name
    return string

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Tool for experimenting with mdr files.')
    parser.add_argument('-p', '--parse-only', default=False, action='store_true',
                        help='Only parse file, do not dump models')
    parser.add_argument('-v', '--verbose', default=False, action='store_true',
                        help='Print more info useful for debugging')
    parser.add_argument('-o', '--outdir', default=os.getcwd(), help='Output path')
    parser.add_argument('file', nargs='?', help='Input file')
    args = parser.parse_args()

    filepath = None
    if args.file is None:
        print("Error, supply a file as parameter")
        sys.exit()
    else:
        filepath = args.file
    
    print("# ", filepath)
    base_name = os.path.splitext(os.path.basename(filepath))[0]
    m = MDR(filepath, base_name, args.outdir, args.parse_only, args.parse_only, args.verbose)

    if not args.parse_only:
        for ob in m.objects:
            with open(os.path.join(args.outdir, "%s_%s.obj" % (ob.base_name, ob.name)), 'wb') as obj_fout:
                obj_fout.write(make_wavefront_obj(ob).encode("ascii"))
            with open(os.path.join(args.outdir, "%s_%s.mtl" % (ob.base_name, ob.name)), 'wb') as mtl_fout:
                mtl_fout.write(make_wavefront_mtl(ob).encode("ascii"))
