**Modding tools for Combat Mission**

Requirements

 - Python 3

To view the help message of scripts:  
python3 brz_magick.py -h

To extract a brz file:  
python3 brz_magick.py -x my_file.brz

To extract a brz file to a specific directory:  
python3 brz_magick.py -x my_file.brz -o C:\Some\other\path

To compress a directory with files into brz:  
python3 brz_magick.py -c mydir

To dump mdr file to OBJ:
python3 unmdr.py crate1.mdr

To only parse mdr:
python3 unmdr.py -p crate1.mdr

