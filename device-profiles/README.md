# Profiles moved

"Legacy" device profiles have been migrated to a new format.

The new repository of devices and profiles can be found here:

https://github.com/tuya-cloudcutter/tuya-cloudcutter.github.io

---

If you'd like to submit a profile you generated, create a pull request **to the repo above**, not `tuya-cloudcutter`.

## Testing custom profiles

After generating a profile, you'll get two files in `profile-classic` directory. You can rename the one in `profile-classic/devices/` however you want, and update its `manufacturer` and `name` strings. Do not change any other fields, as well as the file in `profile-classic/profiles/`.

These two files can be added to [tuya-cloudcutter.github.io](https://github.com/tuya-cloudcutter/tuya-cloudcutter.github.io) repository in a pull request.

To test the profile locally, you can copy the 2 JSONs (without any parent directories) to a subdirectory in `device-profiles`, like this:
```
device-profiles/
├─ your-device-name/
│  ├─ your-device-name.json
│  ├─ oem-bk7231n-dctrl-switch-1.1.0-sdk-2.3.1-40.00.json
```

and run `./tuya-cloudcutter.sh -p your-device-name`.
