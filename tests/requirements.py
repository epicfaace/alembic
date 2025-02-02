from sqlalchemy.testing import exclusions

from alembic.testing.requirements import SuiteRequirements
from alembic.util import sqla_compat


class DefaultRequirements(SuiteRequirements):
    @property
    def alter_column(self):
        return exclusions.skip_if(["sqlite"], "no ALTER COLUMN support")

    @property
    def schemas(self):
        """Target database must support external schemas, and have one
        named 'test_schema'."""

        return exclusions.skip_if(["sqlite", "firebird"], "no schema support")

    @property
    def no_referential_integrity(self):
        """test will fail if referential integrity is enforced"""

        return exclusions.fails_on_everything_except("sqlite")

    @property
    def non_native_boolean(self):
        """test will fail if native boolean is provided"""

        return exclusions.fails_if(
            exclusions.LambdaPredicate(
                lambda config: config.db.dialect.supports_native_boolean
            )
        )

    @property
    def check_constraints_w_enforcement(self):
        return exclusions.fails_on("mysql")

    @property
    def unnamed_constraints(self):
        """constraints without names are supported."""
        return exclusions.only_on(["sqlite"])

    @property
    def fk_names(self):
        """foreign key constraints always have names in the DB"""
        return exclusions.fails_on("sqlite")

    @property
    def no_name_normalize(self):
        return exclusions.skip_if(
            lambda config: config.db.dialect.requires_name_normalize
        )

    @property
    def reflects_fk_options(self):
        return exclusions.only_on(["postgresql", "mysql", "sqlite"])

    @property
    def fk_initially(self):
        """backend supports INITIALLY option in foreign keys"""
        return exclusions.only_on(["postgresql"])

    @property
    def fk_deferrable(self):
        """backend supports DEFERRABLE option in foreign keys"""
        return exclusions.only_on(["postgresql"])

    @property
    def flexible_fk_cascades(self):
        """target database must support ON UPDATE/DELETE..CASCADE with the
        full range of keywords (e.g. NO ACTION, etc.)"""

        return exclusions.skip_if(
            ["oracle"], "target backend has poor FK cascade syntax"
        )

    @property
    def reflects_unique_constraints_unambiguously(self):
        return exclusions.fails_on("mysql", "oracle")

    @property
    def reflects_pk_names(self):
        """Target driver reflects the name of primary key constraints."""

        return exclusions.fails_on_everything_except(
            "postgresql", "oracle", "mssql", "sybase", "sqlite"
        )

    @property
    def postgresql_uuid_ossp(self):
        def check_uuid_ossp(config):
            if not exclusions.against(config, "postgresql"):
                return False
            try:
                config.db.execute("SELECT uuid_generate_v4()")
                return True
            except:
                return False

        return exclusions.only_if(check_uuid_ossp)

    def _has_pg_extension(self, name):
        def check(config):
            if not exclusions.against(config, "postgresql"):
                return False
            count = config.db.scalar(
                "SELECT count(*) FROM pg_extension "
                "WHERE extname='%s'" % name
            )
            return bool(count)

        return exclusions.only_if(check, "needs %s extension" % name)

    @property
    def hstore(self):
        return self._has_pg_extension("hstore")

    @property
    def btree_gist(self):
        return self._has_pg_extension("btree_gist")

    @property
    def autoincrement_on_composite_pk(self):
        return exclusions.skip_if(["sqlite"], "not supported by database")

    @property
    def integer_subtype_comparisons(self):
        """if a compare of Integer and BigInteger is supported yet."""
        return exclusions.skip_if(["oracle"], "not supported by alembic impl")

    @property
    def check_constraint_reflection(self):
        return exclusions.fails_on_everything_except(
            "postgresql",
            "sqlite",
            "oracle",
            self._mysql_and_check_constraints_exist,
        )

    @property
    def mysql_check_reflection_or_none(self):
        # succeed if:
        # 1. SQLAlchemy does not reflect CHECK constraints
        # 2. SQLAlchemy does reflect CHECK constraints, but MySQL does not.
        def go(config):
            return (
                not self._mysql_check_constraints_exist(config)
                or self.sqlalchemy_1115.enabled
            )

        return exclusions.succeeds_if(go)

    @property
    def mysql_timestamp_reflection(self):
        def go(config):
            return (
                not self._mariadb_102(config) or self.sqlalchemy_1115.enabled
            )

        return exclusions.only_if(go)

    def _mariadb_102(self, config):
        return (
            exclusions.against(config, "mysql")
            and sqla_compat._is_mariadb(config.db.dialect)
            and sqla_compat._mariadb_normalized_version_info(config.db.dialect)
            > (10, 2)
        )

    def mysql_check_col_name_change(self, config):
        # MySQL has check constraints that enforce an reflect, however
        # they prevent a column's name from being changed due to a bug in
        # MariaDB 10.2 as well as MySQL 8.0.16
        if exclusions.against(config, "mysql"):
            if sqla_compat._is_mariadb(config.db.dialect):
                mnvi = sqla_compat._mariadb_normalized_version_info
                norm_version_info = mnvi(config.db.dialect)
                return norm_version_info >= (10, 2) and norm_version_info < (
                    10,
                    2,
                    22,
                )
            else:
                norm_version_info = config.db.dialect.server_version_info
                return norm_version_info >= (8, 0, 16)

        else:
            return True

    def _mysql_and_check_constraints_exist(self, config):
        # 1. we have mysql / mariadb and
        # 2. it enforces check constraints
        if exclusions.against(config, "mysql"):
            if sqla_compat._is_mariadb(config.db.dialect):
                mnvi = sqla_compat._mariadb_normalized_version_info
                norm_version_info = mnvi(config.db.dialect)
                return norm_version_info >= (10, 2)
            else:
                norm_version_info = config.db.dialect.server_version_info
                return norm_version_info >= (8, 0, 16)
        else:
            return False

    def _mysql_check_constraints_exist(self, config):
        # 1. we dont have mysql / mariadb or
        # 2. we have mysql / mariadb that enforces check constraints
        return not exclusions.against(
            config, "mysql"
        ) or self._mysql_and_check_constraints_exist(config)

    def _mysql_check_constraints_dont_exist(self, config):
        # 1. we have mysql / mariadb and
        # 2. they dont enforce check constraints
        return not self._mysql_check_constraints_exist(config)

    def _mysql_not_mariadb_102(self, config):
        return exclusions.against(config, "mysql") and (
            not sqla_compat._is_mariadb(config.db.dialect)
            or sqla_compat._mariadb_normalized_version_info(config.db.dialect)
            < (10, 2)
        )
