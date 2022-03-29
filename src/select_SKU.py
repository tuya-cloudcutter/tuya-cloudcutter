import os, sys
import inquirer


def ask(text, dir):
    files = os.listdir(dir)
    return inquirer.prompt([inquirer.List('path', carousel=True, message=text, choices=files)])

if __name__ == "__main__":
    output_file = open(sys.argv[1], "wt")
    profile_dir = "cloudcutter/device-profiles"
    manufacturer = ask("Select the brand of your device", profile_dir)["path"]
    device = ask("Select the article number of your device",  f"{profile_dir}/{manufacturer}")["path"]
    print(f"{manufacturer}/{device}", file=output_file)