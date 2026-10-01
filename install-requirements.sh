#!/usr/bin/env bash
#
# Installs the host-side requirements for tuya-cloudcutter.
#
# All of the actual work now runs inside the Docker container, so the host only
# needs:
#   - docker : to build and run the container
#   - iw     : to move the WiFi adapter into the container's network namespace
#
# This script checks whether each is present and, if not, installs it using the
# system package manager.  It must be run on the Linux host (not inside the
# container) and needs root privileges to install packages.

set -euo pipefail

# ---------------------------------------------------------------------------
# Privilege handling
# ---------------------------------------------------------------------------
SUDO=""
if [ "$(id -u)" -ne 0 ]; then
    if command -v sudo >/dev/null 2>&1; then
        SUDO="sudo"
    else
        echo "[!] This script needs root privileges to install packages."
        echo "    Re-run as root, or install 'sudo'."
        exit 1
    fi
fi

# ---------------------------------------------------------------------------
# Detect the package manager and set the commands / package names to use.
# ---------------------------------------------------------------------------
PM_UPDATE=""
PM_INSTALL=""
DOCKER_PKGS=()
IW_PKG="iw"

if command -v apt-get >/dev/null 2>&1; then
    PM_UPDATE="apt-get update"
    PM_INSTALL="apt-get install -y"
    # On Debian Bookworm the docker CLI ('docker' command) was split out of the
    # 'docker.io' daemon package into a separate 'docker-cli' package, so both are
    # required for a usable install.
    DOCKER_PKGS=(docker.io docker-cli)
elif command -v dnf >/dev/null 2>&1; then
    PM_UPDATE=""
    PM_INSTALL="dnf install -y"
    DOCKER_PKGS=(docker)
elif command -v yum >/dev/null 2>&1; then
    PM_UPDATE=""
    PM_INSTALL="yum install -y"
    DOCKER_PKGS=(docker)
elif command -v pacman >/dev/null 2>&1; then
    PM_UPDATE="pacman -Sy"
    PM_INSTALL="pacman -S --noconfirm --needed"
    DOCKER_PKGS=(docker)
elif command -v zypper >/dev/null 2>&1; then
    PM_UPDATE=""
    PM_INSTALL="zypper install -y"
    DOCKER_PKGS=(docker)
elif command -v apk >/dev/null 2>&1; then
    PM_UPDATE="apk update"
    PM_INSTALL="apk add"
    DOCKER_PKGS=(docker docker-cli)
else
    echo "[!] Could not detect a supported package manager."
    echo "    Please install 'docker' and 'iw' manually, then re-run tuya-cloudcutter.sh."
    exit 1
fi

echo "Using package manager install command: ${PM_INSTALL}"

UPDATED="false"
pm_update_once() {
    if [ -n "${PM_UPDATE}" ] && [ "${UPDATED}" != "true" ]; then
        echo "Refreshing package lists..."
        # shellcheck disable=SC2086
        ${SUDO} ${PM_UPDATE}
        UPDATED="true"
    fi
}

pm_install() {
    pm_update_once
    echo "Installing: $*"
    # shellcheck disable=SC2086
    ${SUDO} ${PM_INSTALL} "$@"
}

# ---------------------------------------------------------------------------
# Docker
# ---------------------------------------------------------------------------
if command -v docker >/dev/null 2>&1; then
    echo "[OK] docker is already installed ($(docker --version 2>/dev/null || echo 'version unknown'))."
else
    echo "docker was not found - installing: ${DOCKER_PKGS[*]}..."
    pm_install "${DOCKER_PKGS[@]}"

    # Forget any cached command locations so a freshly installed docker is found.
    hash -r 2>/dev/null || true

    # Enable and start the docker service if we are running systemd.
    if command -v systemctl >/dev/null 2>&1; then
        echo "Enabling and starting the docker service..."
        ${SUDO} systemctl enable --now docker >/dev/null 2>&1 || \
            echo "[!] Could not enable/start docker via systemctl - you may need to start it manually."
    fi

    # Add the invoking (non-root) user to the docker group so they can run docker
    # without sudo. A re-login is required for this to take effect.
    TARGET_USER="${SUDO_USER:-${USER:-}}"
    if [ -n "${TARGET_USER}" ] && [ "${TARGET_USER}" != "root" ]; then
        if getent group docker >/dev/null 2>&1; then
            echo "Adding user '${TARGET_USER}' to the 'docker' group..."
            ${SUDO} usermod -aG docker "${TARGET_USER}" || true
            echo "    You will need to log out and back in (or reboot) for this to take effect."
        fi
    fi
fi

# ---------------------------------------------------------------------------
# iw (needed by the host launcher to hand the WiFi adapter to the container)
# ---------------------------------------------------------------------------
if command -v iw >/dev/null 2>&1; then
    echo "[OK] iw is already installed."
else
    echo "iw was not found - installing '${IW_PKG}'..."
    pm_install "${IW_PKG}"
fi

hash -r 2>/dev/null || true

# ---------------------------------------------------------------------------
# Verify that everything is actually callable now. Do not claim success unless
# the commands really exist - otherwise a failed or incomplete install would be
# reported as "satisfied".
# ---------------------------------------------------------------------------
MISSING=""
command -v docker >/dev/null 2>&1 || MISSING="${MISSING} docker"
command -v iw >/dev/null 2>&1 || MISSING="${MISSING} iw"

if [ -n "${MISSING}" ]; then
    echo ""
    echo "[!] The following requirements are still not available after installation:${MISSING}"
    echo ""
    echo "    The package manager did not provide a working command above."
    echo "    If 'docker' is the one missing, the distro package may be unavailable or"
    echo "    may have failed to install. Installing Docker from Docker's official"
    echo "    repository is the most reliable option (it supports Raspberry Pi OS):"
    echo "        curl -fsSL https://get.docker.com | sudo sh"
    echo "    or follow https://docs.docker.com/engine/install/debian/"
    echo "    Then re-run this script to install any remaining requirements."
    exit 1
fi

echo ""
echo "All host requirements are satisfied."
echo "  - $(docker --version 2>/dev/null || echo 'docker: installed')"
echo "  - iw: installed"
echo "You can now run: sudo ./tuya-cloudcutter.sh -w <adapter> ..."
