import sys
import os.path
import extract
import haxomatic
import process_storage
import process_app
import pull_schema
import generate_profile_classic

if __name__ == '__main__':
    if not sys.argv[1:]:
        print('Usage: python build_profile.py <full 2M encrypted bin file> <region code=\'us\'> <token=\'None\'>')
        print('region and token are optional.  Region will default to \'us\', token instructions will prompt if needed.')
        print('Note: encrypted bin name must be in the pattern of Manufacturer-Name_Model-and-device-description')
        print('Use dashes in places of spaces, and if a dash (-) is present, replace it with 3 dashes (---)')
        print('There should only be 1 underscore in the filename, separating manufacturer name and model name')
        sys.exit(1)

    region = 'us'
    token = None
    if len(sys.argv) > 2 and sys.argv[2] is not None:
        region = sys.argv[2]
    if len(sys.argv) > 3 and sys.argv[3] is not None:
        token = sys.argv[3]

    file = sys.argv[1]
    output_dir = sys.argv[1].replace('.bin', '')
    base_name = os.path.basename(output_dir)
    dirname = os.path.dirname(file)
    storage_file = os.path.join(dirname, base_name, base_name + '_storage.json')
    app_file = os.path.join(dirname, base_name, base_name + '_app_1.00_decrypted.bin')
    schema_id_file = os.path.join(dirname, base_name, base_name + '_schema_id.txt')
    extracted_location = os.path.join(dirname, base_name)

    print(f"[+] Processing {file=} as {base_name}")

    extract.run(file)
    haxomatic.run(app_file)
    process_storage.run(storage_file)
    process_app.run(app_file)
    pull_schema.run_directory(extracted_location)

    if not os.path.exists(schema_id_file):
        print("[!] Unable to build complete profile as schema remains missing.")
        exit(1)

    generate_profile_classic.run(extracted_location)
