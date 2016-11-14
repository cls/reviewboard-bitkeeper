from __future__ import unicode_literals

import re

from djblets.util.filesystem import is_exe_in_path

from reviewboard.diffviewer.parser import DiffParser, File
from reviewboard.scmtools.core import SCMClient, SCMTool, HEAD, PRE_CREATION, UNKNOWN
from reviewboard.scmtools.errors import (FileNotFoundError, RepositoryNotFoundError)

OPER_PATTERNS = {
    'copied':  re.compile(b'  bk cp (?P<origname>.*) .*'),
    'deleted': re.compile(b'  Delete: (?P<origname>.*)'),
    'moved':   re.compile(b'  Rename: (?P<origname>.*) -> .*'),
}

class BKTool(SCMTool):
    name = 'BitKeeper'
    dependencies = {
        'executables': ['bk']
    }

    def __init__(self, repository):
        super(BKTool, self).__init__(repository)

        if not is_exe_in_path('bk'):
            # This is technically not the right kind of error, but it's the
            # pattern we use with all the other tools.
            raise ImportError

        local_site_name = None

        if repository.local_site:
            local_site_name = repository.local_site.name

        self.client = BKClient(repository.path, local_site_name)

    def get_file(self, path, revision=HEAD, base_commit_id=None, **kwargs):
        if base_commit_id is not None:
            base_commit_id = base_commit_id

        return self.client.cat_file(path, revision, base_commit_id=base_commit_id)

    def parse_diff_revision(self, file_str, revision_str, *args, **kwargs):
        revision = revision_str
        if file_str == '/dev/null':
            revision = PRE_CREATION
        if not revision_str:
            revision = UNKNOWN
        return file_str, revision

    def get_diffs_use_absolute_paths(self):
        return True

    def get_parser(self, data):
        return BKDiffParser(data)

    @classmethod
    def check_repository(cls, path, username=None, password=None, local_site_name=None):
        client = BKClient(path, local_site_name)

        super(BKTool, cls).check_repository(client.path, local_site_name)

        # Create a client. This will fail if the repository doesn't exist.
        BKClient(path, local_site_name)

class BKDiffParser(DiffParser):
    def __init__(self, data):
        self.copies = {}
        self.new_changeset_id = None
        self.orig_changeset_id = None

        return super(BKDiffParser, self).__init__(data)

    def parse_special_header(self, linenum, info):
        header = re.match(b'==== (?P<filename>.*) ====', self.lines[linenum])

        if not header:
            return linenum

        linenum += 2

        filename = info['newFile'] = header.group('filename')

        if filename in self.copies:
            info['origFile'] = self.copies[filename]
            info['copied'] = True
        else:
            info['origFile'] = filename

        if linenum < len(self.lines) and self.lines[linenum].startswith(b'  '):
            for attr, pattern in OPER_PATTERNS.iteritems():
                match = pattern.match(self.lines[linenum])
                if match:
                    origname = match.group('origname')
                    info['origFile'] = origname
                    info['origInfo'] = UNKNOWN
                    info['newInfo'] = UNKNOWN
                    info[attr] = True

                    if attr == 'copied':
                        self.copies[filename] = origname

                    break

        while linenum < len(self.lines) and self.lines[linenum].startswith(b'  '):
            linenum += 1

        return linenum

    def parse_diff_header(self, linenum, info):
        if linenum < len(self.lines) and self.lines[linenum] == b'Binary files differ':
            info['binary'] = True
            info['newInfo'] = UNKNOWN

            linenum += 1

            if linenum + 1 < len(self.lines) and self.lines[linenum].startswith(b'===='):
                info['origInfo'] = PRE_CREATION
                linenum += 2
            else:
                info['origInfo'] = UNKNOWN

        elif linenum + 1 < len(self.lines):
            orig = re.match(b'\-\-\- (?P<filename>(?P<revision>[^/]*).*?)\t.*', self.lines[linenum])
            new  = re.match(b'\+\+\+ (?P<filename>(?P<revision>[^/]*).*?)\t.*', self.lines[linenum + 1])

            if orig and new:
                if orig.group('filename') == b'/dev/null':
                    info['origInfo'] = PRE_CREATION
                else:
                    info['origInfo'] = orig.group('revision')

                info['newInfo'] = new.group('revision')

                linenum += 2

        return linenum

    def get_orig_commit_id(self):
        return self.orig_changeset_id

class BKClient(SCMClient):
    def __init__(self, path, local_site_name=None):
        super(BKClient, self).__init__(path)

        self.local_site_name = local_site_name

    def cat_file(self, path, rev, base_commit_id=None):
        # If the base commit id is provided it should override anything
        # that was parsed from the diffs
        if base_commit_id is not None:
            rev = base_commit_id

        if rev == HEAD:
            rev = '@'

        if path:
            p = self._run_bk(['get', '-pqr' + rev, path])
            contents = p.stdout.read()
            failure = p.wait()

            if not failure:
                return contents

        raise FileNotFoundError(path, rev)

    def _run_bk(self, args):
        return SCMTool.popen(['bk', '-@' + self.path] + args, local_site_name=self.local_site_name)
