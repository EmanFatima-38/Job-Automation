import unittest
from unittest.mock import MagicMock, patch
from app.services.discovery_lock import discovery_lock


class LockTests(unittest.TestCase):
    def test_unlocks_on_failure(self):
        connection = MagicMock()
        connection.scalar.return_value = True
        with patch('app.services.discovery_lock.engine') as engine:
            engine.connect.return_value.__enter__.return_value = connection
            with self.assertRaises(RuntimeError):
                with discovery_lock('user') as acquired:
                    self.assertTrue(acquired)
                    raise RuntimeError('worker failed')
        self.assertIn('pg_advisory_unlock', str(connection.execute.call_args.args[0]))

    def test_other_worker_owner_is_respected(self):
        connection = MagicMock()
        connection.scalar.return_value = False
        with patch('app.services.discovery_lock.engine') as engine:
            engine.connect.return_value.__enter__.return_value = connection
            with discovery_lock('user') as acquired:
                self.assertFalse(acquired)
        connection.execute.assert_not_called()
