# Cloudcutter profile building

You can now generate universal and classic profile by using a series of scripts that will build working profiles provided enough information is present in the dumped bins.  You will need a full 2M bin dump, including storage in order to properly build profiles.  Decrypted app-only or bins without storage are no longer acceptible, as they are missing crucial parts for building a complete profile.

## Usage

The only file you should need to run is `build_profile.py`, all other necessary scripts will be called from that script, and will properly guide you through making a complete and usable profile, should all necessary data be present.

Before you begin, you must name your file to match a specific pattern.  The format is `Manufacturer-Name_Model-name-and-number---with---dashes-Device-Type`.  There should be no spaces, and both a manufacturer and model must be present, separated by an underscore (_).  If there is no specific manufacturer, please use `Tuya-Generic` as the manufacturer.  Spaces should be replaced with dashes (-), and dashes (-) should be replaced with 3 consecutive dashes (---).

To run, execute `py build_profile.py <path_to_full_encrypted_2m.bin> [<token>]` (Example: `py build_profile Tuya-Generic_DS---101-Light-Switch` or `py build_profile Tuya-Generic_DS---101-Light-Switch eu`) where token is optional.  If the device schema is not present in storage, you will be walked through connecting to the Tuya API to retreive a valid schema for the device.  Please read all instructions presented on the screen.  Token is not needed to be known in advance.  If one is needed, the on-screen instructions will guide you through the process.

If successful, the script will extract and decrypt your bin to a subdirectory matching the original filename, create several files for collected pieces of data, and create a `profile-classic` and `profile-universal` directory within.
