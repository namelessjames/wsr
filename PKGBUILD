# Maintainer: namelessjames <your-email@example.com>
pkgname=wsr
pkgver=0.1.0
pkgrel=1
pkgdesc="Wayland Session Recorder - zeichnet Klicks, Screenshots und Tastenanschlaege auf"
arch=('any')
url="https://github.com/namelessjames/wsr"
license=('MIT')
depends=('python' 'python-evdev' 'python-pillow' 'python-yaml')
makedepends=('python-build' 'python-installer' 'python-wheel')
optdepends=(
    'grim: Screenshot-Tool fuer wlroots/Hyprland'
    'gnome-screenshot: Screenshot-Tool fuer GNOME'
)
source=("$pkgname-$pkgver.tar.gz::$url/archive/v$pkgver.tar.gz")
sha256sums=('SKIP')

build() {
    cd "$pkgname-$pkgver"
    python -m build --wheel --no-isolation
}

package() {
    cd "$pkgname-$pkgver"
    python -m installer --destdir="$pkgdir" dist/*.whl
    install -Dm644 LICENSE "$pkgdir/usr/share/licenses/$pkgname/LICENSE"
}
