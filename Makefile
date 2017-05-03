all:
	pyinstaller --onefile --hidden-import io_scene_mdr --add-data io_scene_mdr:io_scene_mdr unmdr.py
	pyinstaller --onefile --hidden-import io_scene_mdr --add-data io_scene_mdr:io_scene_mdr brz_magick.py
