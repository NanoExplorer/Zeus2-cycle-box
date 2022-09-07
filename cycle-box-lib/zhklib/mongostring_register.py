import shutil
import argparse
import os
from zhklib.common import CONFIG_FOLDER


def main():
    parser = argparse.ArgumentParser(description="set your default mongo string file")
    parser.add_argument('file', type=str, help="Path to the mongo string file you want to set as your default")

    args = parser.parse_args()
    zfolder = CONFIG_FOLDER
    try: 
        os.mkdir(zfolder)
    except FileExistsError:
        pass
    f = args.file
    shutil.copy(f, zfolder + "mongostring")


if __name__ == "__main__":
    main()