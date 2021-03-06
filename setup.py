#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
There are four relevant customizations to the standard distutils installation
process: (1) allowing separate installations of aeidon and gaupol, (2) writing
the aeidon.paths module, (3) handling translating of various files and
(4) installing extensions.

(1) Allowing separate installations of aeidon and gaupol are handled through
    global options --with-aeidon, --without-aeidon, --with-gaupol and
    --without-gaupol. See 'python3 setup.py --help' and the file
    'README.aeidon' for documentation and the Distribution class defined in
    this file for the implementation and logic of how that is handled.

(2) Gaupol finds non-Python files based on the paths written in module
    aeidon.paths. In aeidon/paths.py the paths default to the ones in the
    source directory. During the 'install_lib' command the file gets rewritten
    to build/aeidon/paths.py with the installation paths and that file will be
    installed. The paths are based on variable 'install_data' with the 'root'
    variable stripped if it is given. If doing distro-packaging, make sure this
    file gets correctly written.

(3) During installation, the .po files are compiled into .mo files, the desktop
    file, pattern files and extension metadata files are translated. This
    requires gettext and intltool, more specifically, executables 'msgfmt' and
    'intltool-merge' in $PATH.

(4) Extensions are installed under the data directory. All python code included
    in the extensions are compiled during the 'install_data' command, using the
    same arguments for 'byte_compile' as used by the 'install_lib' command. If
    the 'install_lib' command was given the '--no-compile' option, then
    extensions are not compiled either.
"""

import distutils.command.clean
import distutils.command.install
import distutils.command.install_data
import distutils.command.install_lib
import distutils.command.sdist
import glob
import os
import re
import shutil
import sys
import tarfile
import tempfile

clean = distutils.command.clean.clean
distribution = distutils.dist.Distribution
install = distutils.command.install.install
install_data = distutils.command.install_data.install_data
install_lib = distutils.command.install_lib.install_lib
log = distutils.log
running_py2exe = "py2exe" in sys.argv
sdist = distutils.command.sdist.sdist

if running_py2exe:
    # py2exe patches the Distribution class, so we need to import py2exe
    # here and subclass the patched Distribution class ourselves.
    import py2exe
    distribution = py2exe.Distribution

global_options = (
    ("mandir=", None, ("relative installation directory for man pages "
                       "(defaults to 'share/man')")),

    ("with-aeidon", None, "install the aeidon package"),
    ("without-aeidon", None, "don't install the aeidon package"),
    ("with-gaupol", None, "install the gaupol package"),
    ("without-gaupol", None, "don't install the gaupol package"),
    ("with-iso-codes", None, "install iso-codes XML files"),
    ("without-iso-codes", None, "don't install iso-codes XML files"))

negative_opt = {"without-aeidon": "with-aeidon",
                "without-gaupol": "with-gaupol",
                "without-iso-codes": "with-iso-codes"}

distribution.global_options.extend(global_options)
distribution.negative_opt.update(negative_opt)


def get_aeidon_version():
    """Return version number from aeidon/__init__.py."""
    path = os.path.join("aeidon", "__init__.py")
    text = open(path, "r", encoding="utf_8").read()
    return re.search(r"__version__ *= *['\"](.*?)['\"]", text).group(1)

def get_gaupol_version():
    """Return version number from gaupol/__init__.py."""
    path = os.path.join("gaupol", "__init__.py")
    text = open(path, "r", encoding="utf_8").read()
    return re.search(r"__version__ *= *['\"](.*?)['\"]", text).group(1)

def run_command_or_exit(command):
    """Run command in shell and raise SystemExit if it fails."""
    if os.system(command) != 0:
        log.error("command {} failed".format(repr(command)))
        raise SystemExit(1)

def run_command_or_warn(command):
    """Run command in shell and raise SystemExit if it fails."""
    if os.system(command) != 0:
        log.warn("command {} failed".format(repr(command)))


class Clean(clean):

    """Command to remove files and directories created."""

    def run(self):
        """Remove files and directories listed in manifests/clean."""
        clean.run(self)
        fobj = open(os.path.join("manifests", "clean.manifest"), "r")
        for targets in (glob.glob(x.strip()) for x in fobj):
            for target in filter(os.path.isdir, targets):
                log.info("removing '{}'".format(target))
                if not self.dry_run:
                    shutil.rmtree(target)
            for target in filter(os.path.isfile, targets):
                log.info("removing '{}'".format(target))
                if not self.dry_run:
                    os.remove(target)
        fobj.close()


class Distribution(distribution):

    """The core controller of distutils commands."""

    def __find_data_files(self, name):
        """Find data files to install for name."""
        fok = lambda x: not x.endswith((".in", ".pyc"))
        basename = "{}.manifest".format(name)
        fobj = open(os.path.join("manifests", basename), "r")
        for line in (x.strip() for x in fobj):
            if not line: continue
            if line.startswith("["):
                dest = line[1:-1]
                continue
            files = list(filter(fok, glob.glob(line)))
            files = list(filter(os.path.isfile, files))
            assert files
            self.data_files.append((dest, files))
        fobj.close()

    def __find_man_pages(self):
        """Find man pages to install."""
        mandir = self.mandir
        while mandir.endswith("/"):
            mandir = mandir[:-1]
        dest = "/".join((mandir, "man1"))
        self.data_files.append((dest, ("doc/gaupol.1",)))

    def __find_packages(self, name):
        """Find Python packages to install for name."""
        for (root, dirs, files) in os.walk(name):
            init_path = os.path.join(root, "__init__.py")
            if not os.path.isfile(init_path): continue
            path = root.replace(os.sep, ".")
            if path.endswith(".test"): continue
            self.packages.append(path[path.find(name):])

    def __find_scripts(self, name):
        """Find scripts to install for name."""
        if name == "gaupol":
            self.scripts.append("bin/gaupol")

    def __init__(self, attrs=None):
        """Initialize a Distribution object."""
        self.mandir = "share/man"
        self.with_aeidon = True
        self.with_gaupol = True
        self.with_iso_codes = True
        value = distribution.__init__(self, attrs)
        self.data_files = []
        self.packages = []
        self.scripts = []
        return value

    def parse_command_line(self):
        """Parse commands and options given as arguments."""
        value = distribution.parse_command_line(self)
        # Configuration files are parsed before the command line,
        # so once the command line is parsed, all options have
        # their final values and thus files corresponding to
        # the packages to install can finally be set.
        if self.with_aeidon:
            self.__find_data_files("aeidon")
            self.__find_packages("aeidon")
            if self.with_iso_codes:
                self.__find_data_files("iso-codes")
        if self.with_gaupol:
            self.__find_data_files("gaupol")
            self.__find_man_pages()
            self.__find_packages("gaupol")
            self.__find_scripts("gaupol")
        # Redefine name, version and requires metadata attributes.
        # These are used in the egg-info file written by distutils.
        # While egg-info files appear completely useless, it needs
        # to be ensured that if aeidon and gaupol are installed
        # separately, they install differently named egg-info files
        # in order to avoid overwriting each other.
        if self.with_gaupol:
            self.metadata.name = "gaupol"
            self.metadata.version = get_gaupol_version()
        else: # without gaupol
            self.metadata.name = "aeidon"
            self.metadata.version = get_aeidon_version()
        return value

    def parse_config_files(self, filenames=None):
        """Parse options from configuration files."""
        value = distribution.parse_config_files(self, filenames)
        strtobool = distutils.util.strtobool
        for option in ("with_aeidon", "with_gaupol", "with_iso_codes"):
            value = getattr(self, option)
            if isinstance(value, str):
                setattr(self, option, strtobool(value))
        return value


class Documentation(distutils.cmd.Command):

    """Command to build documentation from source code."""

    description = "build documentation from source code"
    user_options = [("format=", "f",
                     "type of documentation to create (try 'html')")]

    def initialize_options(self):
        """Initialize default values for options."""
        self.format = None

    def finalize_options(self):
        """Ensure that options have valid values."""
        if self.format is None:
            log.warn("format not specified, using 'html'")
            self.format = "html"

    def run(self):
        """Build documentation from source code."""
        os.chdir(os.path.join("doc", "sphinx"))
        if not self.dry_run:
            run_command_or_exit("make clean")
            run_command_or_exit("python{:d}.{:d} autogen.py aeidon gaupol"
                                .format(*sys.version_info[:2]))

            run_command_or_exit("make {}".format(self.format))


class Install(install):

    """Command to install everything."""

    def run(self):
        """Install everything and update the desktop file database."""
        install.run(self)
        if not self.distribution.with_gaupol: return
        get_command_obj = self.distribution.get_command_obj
        root = get_command_obj("install").root
        data_dir = get_command_obj("install_data").install_dir
        # Assume we're actually installing if --root was not given.
        if (root is not None) or (data_dir is None): return
        directory = os.path.join(data_dir, "share", "applications")
        log.info("updating desktop database in '{}'".format(directory))
        run_command_or_warn('update-desktop-database "{}"'.format(directory))


class InstallData(install_data):

    """Command to install data files."""

    def __build_extensions(self):
        """Build all Python code files in extensions."""
        get_command_obj = self.distribution.get_command_obj
        if not get_command_obj("install_lib").compile: return
        optimize = get_command_obj("install_lib").optimize
        data_dir = get_command_obj("install_data").install_dir
        data_dir = os.path.join(data_dir, "share", "gaupol")
        files = glob.glob("{}/extensions/*/*.py".format(data_dir))
        distutils.util.byte_compile(files, optimize, self.force, self.dry_run)

    def __get_desktop_file(self):
        """Return a tuple for translated desktop file."""
        path = os.path.join("data", "gaupol.desktop")
        if not running_py2exe:
            run_command_or_exit("intltool-merge -d po {}.in {}"
                                .format(path, path))

        return ("share/applications", (path,))

    def __get_extension_file(self, extension, extension_file):
        """Return a tuple for translated extension metadata file."""
        assert extension_file.endswith(".in")
        path = extension_file[:-3]
        if not running_py2exe:
            run_command_or_exit("intltool-merge -d po {}.in {}"
                                .format(path, path))

        return ("share/gaupol/extensions/{}".format(extension), (path,))

    def __get_mo_file(self, po_file):
        """Return a tuple for compiled .mo file."""
        locale = os.path.basename(po_file[:-3])
        mo_dir = os.path.join("locale", locale, "LC_MESSAGES")
        if not os.path.isdir(mo_dir):
            log.info("creating {}".format(mo_dir))
            os.makedirs(mo_dir)
        mo_file = os.path.join(mo_dir, "gaupol.mo")
        dest_dir = os.path.join("share", mo_dir)
        if not running_py2exe:
            log.info("compiling '{}'".format(mo_file))
            run_command_or_exit("msgfmt {} -o {}"
                                .format(po_file, mo_file))

        return (dest_dir, (mo_file,))

    def __get_pattern_file(self, pattern_file):
        """Return a tuple for the translated pattern file."""
        assert pattern_file.endswith(".in")
        path = pattern_file[:-3]
        if not running_py2exe:
            run_command_or_exit("intltool-merge -d po {}.in {}"
                                .format(path, path))

        return ("share/gaupol/patterns", (path,))

    def run(self):
        """Install data files after translating them."""
        if self.distribution.with_aeidon:
            for po_file in glob.glob("po/*.po"):
                self.data_files.append(self.__get_mo_file(po_file))
            for pattern_file in glob.glob("data/patterns/*.in"):
                self.data_files.append(self.__get_pattern_file(pattern_file))
        if self.distribution.with_gaupol:
            for extension in os.listdir("data/extensions"):
                pattern = "data/extensions/{}/*.extension.in"
                pattern = pattern.format(extension)
                for extension_file in glob.glob(pattern):
                    t = self.__get_extension_file(extension, extension_file)
                    self.data_files.append(t)
            self.data_files.append(self.__get_desktop_file())
        install_data.run(self)
        if self.distribution.with_gaupol:
            self.__build_extensions()


class InstallLib(install_lib):

    """Command to install library files."""

    def __write_paths_module(self):
        """Write installation paths to build/aeidon/paths.py."""
        get_command_obj = self.distribution.get_command_obj
        root = get_command_obj("install").root
        prefix = get_command_obj("install").install_data
        # Allow --root to be used like $DESTDIR.
        if root is not None:
            prefix = os.path.abspath(prefix)
            prefix = prefix.replace(os.path.abspath(root), "")
        data_dir = os.path.join(prefix, "share", "gaupol")
        locale_dir = os.path.join(prefix, "share", "locale")
        # Write changes to the aeidon.paths module.
        path = os.path.join(self.build_dir, "aeidon", "paths.py")
        text = open(path, "r", encoding="utf_8").read()
        patt = "DATA_DIR = get_data_directory()"
        repl = "DATA_DIR = {}".format(repr(data_dir))
        text = text.replace(patt, repl)
        assert text.count(repr(data_dir)) > 0
        patt = "LOCALE_DIR = get_locale_directory()"
        repl = "LOCALE_DIR = {}".format(repr(locale_dir))
        text = text.replace(patt, repl)
        assert text.count(repr(locale_dir)) > 0
        open(path, "w", encoding="utf_8").write(text)

    def install(self):
        """Install library files after writing changes."""
        if self.distribution.with_aeidon:
            self.__write_paths_module()
        return install_lib.install(self)


class SDistGna(sdist):

    description = "create source distribution for gna.org"

    def finalize_options(self):
        """Set the distribution directory to 'dist/X.Y'."""
        version = get_gaupol_version()
        sdist.finalize_options(self)
        branch = ".".join(version.split(".")[:2])
        self.dist_dir = os.path.join(self.dist_dir, branch)

    def run(self):
        version = get_gaupol_version()
        if os.path.isfile("ChangeLog"):
            os.remove("ChangeLog")
        run_command_or_exit("tools/generate-change-log > ChangeLog")
        assert os.path.isfile("ChangeLog")
        assert open("ChangeLog", "r").read().strip()
        sdist.run(self)
        basename = "gaupol-{}".format(version)
        tarballs = os.listdir(self.dist_dir)
        os.chdir(self.dist_dir)
        # Compare tarball contents with working copy.
        temp_dir = tempfile.gettempdir()
        test_dir = os.path.join(temp_dir, basename)
        tobj = tarfile.open(tarballs[-1], "r")
        for member in tobj.getmembers():
            tobj.extract(member, temp_dir)
        log.info("comparing tarball (tmp) with working copy (../..)")
        os.system('diff -qr -x ".*" -x "*.pyc" ../.. {}'.format(test_dir))
        response = input("Are all files in the tarball [Y/n]? ")
        if response.lower() == "n":
            raise SystemExit("Must edit MANIFEST.in")
        shutil.rmtree(test_dir)
        # Create extra distribution files.
        os.system("xz {}.tar".format(basename))
        log.info("calculating md5sums")
        run_command_or_exit("md5sum * > {}.md5sum".format(basename))
        log.info("creating '{}.changes'".format(basename))
        source = os.path.join("..", "..", "ChangeLog")
        shutil.copyfile(source, "{}.changes".format(basename))
        log.info("creating '{}.news'".format(basename))
        source = os.path.join("..", "..", "NEWS")
        shutil.copyfile(source, "{}.news".format(basename))
        log.info("signing '{}.tar.xz'".format(basename))
        run_command_or_exit("gpg --detach {}.tar.xz".format(basename))


setup_kwargs = dict(
    name="gaupol",
    version=get_gaupol_version(),
    platforms=("Platform Independent",),
    author="Osmo Salomaa",
    author_email="otsaloma@iki.fi",
    url="http://home.gna.org/gaupol/",
    description="Editor for text-based subtitle files",
    license="GPL",
    distclass=Distribution,
    cmdclass={
        "clean": Clean,
        "doc": Documentation,
        "install": Install,
        "install_data": InstallData,
        "install_lib": InstallLib,
        "sdist_gna": SDistGna,
        })

if __name__ == "__main__":
    os.chdir(os.path.dirname(__file__) or ".")
    distutils.core.setup(**setup_kwargs)
