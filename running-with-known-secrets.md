# Running with known secrets

## Why would this be useful?

If you have a device that would normally require serial flashing (patched devices), but you don't have access to all the bootstrapping pins (common on RTL8720CF), but can access TX2 and GND (minimum needed to read UART logs).

## When can I use this?

You can only use this method if you know

- AuthKey (32 characters if from Tuya, 16 characters if overridden by CloudCutter)
- UUID (16 characters if from Tuya, 12 characters if overridden by CloudCutter)
- PSKKey (37 characters if from Tuya, empty string if overridden by CloudCutter)

## How can I find the secrets necessary?

- UUID - This can be found one of two ways:
  - Via iot tuya account, similar to finding the local/secret keys via the instructions from [Tiny Tuya](https://github.com/jasonacox/tinytuya#setup-wizard---getting-local-keys) method 3 - Tuya Account
  - Via uart logging (not all devices)
- AuthKey
  - Via uart logging (not all devices)
- PSKKey
  - Via API, included when running profile-building's `pull_schema` (requires a Tuya token, see instructions included with script).  Requires already having UUID and AuthKey

## Finding secrets via UART logging

Some devices will output a string on their UART logging (usually on UART_LOG_TX / TX2 [Pin P0 on Beken, Pin PA16 on RTL8720CF])

Look for a logged line that has a group of 3 strings with random characters that looks something like `upd product_id type:1 keyxxxxxxxxxxxxx abcd1234e5566f78 6W9ckhSD4v1PB8Jwk8O1OVoiTzsdyLh7`.

- The first string of 16 characters is either the Firmware Key, Product Key, or Factory Pin.  This isn't needed, but helpful for identifying the pattern for the other two fields.
- The second string of 16 characters is the UUID.  It will consist of numbers and lower case letters (usually just a-f, but not guaranteed).
- The third string of 32 characters is the AuthKey.  It will consist of numbers and both upper and lower case letters.  This is currently the only known way to find this value.

## I have all the needed secrets, how do I proceed?

You can proceed by running CloudCutter with the `-a` (AuthKey), `-u` (UUID), and `-k` (PSKKey) parameters.  A profile is still necessary to help verify the available firmware to flash, but the exploit is not needed or run if you provide all three fields.
