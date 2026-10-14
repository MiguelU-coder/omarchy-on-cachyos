import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


def run(*args, **kwargs):
    return subprocess.run(args, text=True, capture_output=True, **kwargs)


class AdapterTests(unittest.TestCase):
    def test_bash_syntax(self):
        for path in [*ROOT.glob('bin/*.sh'), ROOT / 'pkgbuilds/omarchy-cachyos/PKGBUILD']:
            result = run('bash', '-n', str(path))
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_help_from_unrelated_directory(self):
        result = run('bash', str(ROOT / 'bin/install-omarchy-on-cachyos.sh'), '--help', cwd='/tmp')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('--prepare-only', result.stdout)

    def test_rejects_unreviewed_version_without_creating_source(self):
        with tempfile.TemporaryDirectory(prefix='omarchy test ') as tmp:
            target = Path(tmp) / 'source'
            result = run('bash', str(ROOT / 'bin/fetch-omarchy.sh'), 'main',
                         env={**os.environ, 'OMARCHY_SOURCE_DIR': str(target)}, cwd='/tmp')
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(target.exists())

    def test_does_not_delete_existing_non_git_directory(self):
        with tempfile.TemporaryDirectory(prefix='omarchy test ') as tmp:
            sentinel = Path(tmp) / 'keep.txt'
            sentinel.write_text('keep me')
            result = run('bash', str(ROOT / 'bin/fetch-omarchy.sh'),
                         env={**os.environ, 'OMARCHY_SOURCE_DIR': tmp}, cwd='/tmp')
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(sentinel.read_text(), 'keep me')

    def test_pacman_config_is_repeatable_and_preserves_cachyos(self):
        original = ('[options]\nArchitecture = auto\nIgnorePkg = custom\n'
                    '[cachyos]\nInclude = /etc/pacman.d/cachyos-mirrorlist\n'
                    '[core]\nInclude = /etc/pacman.d/mirrorlist\n'
                    '[omarchy] # old adapter\nSigLevel = Optional TrustedOnly\nServer = OLD\n'
                    '[extra]\nInclude = /etc/pacman.d/mirrorlist\n')
        result = run('awk', '-f', str(ROOT / 'bin/pacman-config.awk'), input=original)
        self.assertEqual(result.returncode, 0, result.stderr)
        rendered = result.stdout
        repeated = run('awk', '-f', str(ROOT / 'bin/pacman-config.awk'), input=rendered)
        self.assertEqual(rendered, repeated.stdout)
        self.assertEqual(rendered.count('[omarchy]'), 1)
        self.assertNotIn('Server = OLD', rendered)
        self.assertIn('IgnorePkg = custom', rendered)
        self.assertIn('Include = /etc/pacman.d/cachyos-mirrorlist', rendered)
        self.assertIn('[extra]', rendered)
        self.assertLess(rendered.index('[omarchy]'), rendered.index('[cachyos]'))

    def test_recipe_version_and_commit_match_downloader(self):
        result = run('bash', '-c', 'source "$1"; source "$2"; '
                     '[[ $OMARCHY_VERSION == "$pkgver" && $OMARCHY_COMMIT == "$_commit" ]]',
                     'bash', str(ROOT / 'bin/release.sh'), str(ROOT / 'pkgbuilds/omarchy-cachyos/PKGBUILD'))
        self.assertEqual(result.returncode, 0, result.stderr)

    @unittest.skipUnless(os.environ.get('OMARCHY_TEST_SOURCE'), 'Set OMARCHY_TEST_SOURCE to the verified upstream checkout')
    def test_real_upstream_package_staging(self):
        source = Path(os.environ['OMARCHY_TEST_SOURCE']).resolve()
        with tempfile.TemporaryDirectory(prefix='omarchy package test ') as tmp:
            directory = Path(tmp)
            (directory / 'src').mkdir()
            (directory / 'src/omarchy').symlink_to(source, target_is_directory=True)
            (directory / 'tools').mkdir()
            mock = directory / 'tools/magick'
            # Asset generation is mocked; this test checks staging, not image rendering.
            mock.write_text('#!/bin/bash\noutput=${!#}\n: > "${output#PNG32:}"\n')
            mock.chmod(0o755)
            env = {**os.environ, 'srcdir': str(directory / 'src'), 'pkgdir': str(directory / 'pkg'),
                   'PATH': str(directory / 'tools') + ':' + os.environ['PATH']}
            result = run('bash', '-euo', 'pipefail', '-c', 'source "$1"; package',
                         'bash', str(ROOT / 'pkgbuilds/omarchy-cachyos/PKGBUILD'), env=env)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            payload = directory / 'pkg'
            self.assertTrue((payload / 'usr/share/omarchy/config/hypr/hyprland.lua').is_file())
            self.assertTrue((payload / 'usr/share/omarchy/shell').is_dir())
            self.assertTrue((payload / 'usr/share/wayland-sessions/omarchy.desktop').is_file())
            self.assertTrue((payload / 'usr/bin/omarchy-update').stat().st_mode & 0o111)
            for forbidden in ('boot', 'etc/mkinitcpio.conf.d', 'etc/limine-entry-tool.d',
                              'etc/pacman.conf', 'etc/os-release', 'etc/sudoers.d', 'etc/pam.d',
                              'etc/sddm.conf', 'etc/sddm.conf.d', 'etc/snapper', 'etc/skel'):
                self.assertFalse((payload / forbidden).exists(), forbidden)
            self.assertNotIn('/user/default-keyring.sh',
                             (payload / 'usr/share/omarchy/install/user/all.sh').read_text())
            self.assertNotIn('omarchy-migrate', (payload / 'usr/bin/omarchy-update').read_text())

    @unittest.skipUnless(os.environ.get('OMARCHY_TEST_SOURCE'), 'Requires verified upstream checkout')
    def test_prepare_from_unrelated_directory_and_reject_dirty_source(self):
        with tempfile.TemporaryDirectory(prefix='omarchy download test ') as tmp:
            target = Path(tmp) / 'source with spaces'
            cloned = run('git', 'clone', '--quiet', '--no-hardlinks',
                         os.environ['OMARCHY_TEST_SOURCE'], str(target))
            self.assertEqual(cloned.returncode, 0, cloned.stderr)
            env = {**os.environ, 'OMARCHY_SOURCE_DIR': str(target)}
            args = ('bash', str(ROOT / 'bin/install-omarchy-on-cachyos.sh'), '--prepare-only')
            result = run(*args, env=env, cwd='/tmp')
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            (target / 'uncommitted.txt').write_text('preserve this file')
            result = run(*args, env=env, cwd='/tmp')
            self.assertNotEqual(result.returncode, 0)
            self.assertTrue((target / 'uncommitted.txt').exists())


if __name__ == '__main__':
    unittest.main(verbosity=2)
