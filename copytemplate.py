import os
import pathlib

import dotenv

import .dynalist

def main():
    env_path = pathlib.Path('.')/'secrets.env'
    dotenv.load_dotenv(dotenv_path=env_path)

    print(os.getenv("DYNALIST_KEY"))


if __name__ == "__main__":
    main()
