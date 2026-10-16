import subprocess
import sys
import unittest
import uuid
from single_instance import SingleInstance


class SingleInstanceTests(unittest.TestCase):
    def test_duplicate_wakes_primary_and_release_allows_restart(self):
        name = 'Local\\MyServant.Test.' + uuid.uuid4().hex
        first = SingleInstance(name)
        second = None
        try:
            self.assertTrue(first.primary)
            second = SingleInstance(name)
            self.assertFalse(second.primary)
            self.assertTrue(first.restore_requested())
            self.assertFalse(first.restore_requested())
        finally:
            if second:
                second.close()
            first.close()
        restarted = SingleInstance(name)
        try:
            self.assertTrue(restarted.primary)
        finally:
            restarted.close()

    def test_other_process_does_not_become_primary(self):
        name = 'Local\\MyServant.Test.' + uuid.uuid4().hex
        first = SingleInstance(name)
        try:
            code = 'import sys; from single_instance import SingleInstance; i=SingleInstance(sys.argv[1]); duplicate=not i.primary; i.close(); sys.exit(0 if duplicate else 1)'
            result = subprocess.run([sys.executable, '-c', code, name], capture_output=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(first.restore_requested())
        finally:
            first.close()
