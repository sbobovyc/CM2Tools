all:
	pyinstaller --onefile --hidden-import io_scene_mdr --add-data io_scene_mdr/:. unmdr.py
	pyinstaller --onefile brz_magick.py
