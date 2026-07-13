from importlib import import_module
from unittest.mock import Mock

from django.test import SimpleTestCase

migration = import_module("market.migrations.0007_remove_unimplemented_reversal")


class TransferMigrationGuardTests(SimpleTestCase):
    def _migration_apps(self, *, unsupported_kind=False, legacy_link=False):
        transfer = Mock()
        transfer.objects.exclude.return_value.exists.return_value = unsupported_kind
        transfer.objects.filter.return_value.exists.return_value = legacy_link
        apps = Mock()
        apps.get_model.return_value = transfer
        return apps, transfer

    def test_legacy_reversal_link_fails_closed_even_for_supported_kind(self):
        apps, transfer = self._migration_apps(legacy_link=True)

        with self.assertRaisesRegex(RuntimeError, "반전 연결 데이터"):
            migration.reject_unsupported_transfer_rows(apps, schema_editor=None)

        transfer.objects.exclude.assert_called_once_with(kind__in=("ISSUE", "USER_TRANSFER"))
        transfer.objects.filter.assert_called_once_with(reversal_of_id__isnull=False)

    def test_clean_legacy_state_is_allowed(self):
        apps, _transfer = self._migration_apps()

        migration.reject_unsupported_transfer_rows(apps, schema_editor=None)

    def test_destructive_runpython_operation_is_explicitly_irreversible(self):
        operation = migration.Migration.operations[0]

        self.assertFalse(operation.reversible)
