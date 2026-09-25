{
  cpu = 4;
  memory = 24;
  # amd64 イメージ（標準 Compose の linux/x86_64 service など）を QEMU ではなく
  # Rosetta で実行する。QEMU では x86 の Chromium がクラッシュする。
  rosetta = true;
}
