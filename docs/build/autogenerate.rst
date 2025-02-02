Auto Generating Migrations
===========================

Alembic can view the status of the database and compare against the table metadata
in the application, generating the "obvious" migrations based on a comparison.  This
is achieved using the ``--autogenerate`` option to the ``alembic revision`` command,
which places so-called *candidate* migrations into our new migrations file.  We
review and modify these by hand as needed, then proceed normally.

To use autogenerate, we first need to modify our ``env.py`` so that it gets access
to a table metadata object that contains the target.  Suppose our application
has a :ref:`declarative base <sqla:declarative_toplevel>`
in ``myapp.mymodel``.  This base contains a :class:`~sqlalchemy.schema.MetaData` object which
contains :class:`~sqlalchemy.schema.Table` objects defining our database.  We make sure this
is loaded in ``env.py`` and then passed to :meth:`.EnvironmentContext.configure` via the
``target_metadata`` argument.   The ``env.py`` sample script used in the
generic template already has a
variable declaration near the top for our convenience, where we replace ``None``
with our :class:`~sqlalchemy.schema.MetaData`.  Starting with::

    # add your model's MetaData object here
    # for 'autogenerate' support
    # from myapp import mymodel
    # target_metadata = mymodel.Base.metadata
    target_metadata = None

we change to::

    from myapp.mymodel import Base
    target_metadata = Base.metadata

.. note::

  The above example refers to the **generic alembic env.py template**, e.g.
  the one created by default when calling upon ``alembic init``, and not
  the special-use templates such as ``multidb``.   Please consult the source
  code and comments within the ``env.py`` script directly for specific
  guidance on where and how the autogenerate metadata is established.

If we look later in the script, down in ``run_migrations_online()``,
we can see the directive passed to :meth:`.EnvironmentContext.configure`::

    def run_migrations_online():
        engine = engine_from_config(
                    config.get_section(config.config_ini_section), prefix='sqlalchemy.')

        with engine.connect() as connection:
            context.configure(
                        connection=connection,
                        target_metadata=target_metadata
                        )

            with context.begin_transaction():
                context.run_migrations()

We can then use the ``alembic revision`` command in conjunction with the
``--autogenerate`` option.  Suppose
our :class:`~sqlalchemy.schema.MetaData` contained a definition for the ``account`` table,
and the database did not.  We'd get output like::

    $ alembic revision --autogenerate -m "Added account table"
    INFO [alembic.context] Detected added table 'account'
    Generating /path/to/foo/alembic/versions/27c6a30d7c24.py...done

We can then view our file ``27c6a30d7c24.py`` and see that a rudimentary migration
is already present::

    """empty message

    Revision ID: 27c6a30d7c24
    Revises: None
    Create Date: 2011-11-08 11:40:27.089406

    """

    # revision identifiers, used by Alembic.
    revision = '27c6a30d7c24'
    down_revision = None

    from alembic import op
    import sqlalchemy as sa

    def upgrade():
        ### commands auto generated by Alembic - please adjust! ###
        op.create_table(
        'account',
        sa.Column('id', sa.Integer()),
        sa.Column('name', sa.String(length=50), nullable=False),
        sa.Column('description', sa.VARCHAR(200)),
        sa.Column('last_transaction_date', sa.DateTime()),
        sa.PrimaryKeyConstraint('id')
        )
        ### end Alembic commands ###

    def downgrade():
        ### commands auto generated by Alembic - please adjust! ###
        op.drop_table("account")
        ### end Alembic commands ###

The migration hasn't actually run yet, of course.  We do that via the usual ``upgrade``
command.   We should also go into our migration file and alter it as needed, including
adjustments to the directives as well as the addition of other directives which these may
be dependent on - specifically data changes in between creates/alters/drops.

What does Autogenerate Detect (and what does it *not* detect?)
--------------------------------------------------------------

The vast majority of user issues with Alembic centers on the topic of what
kinds of changes autogenerate can and cannot detect reliably, as well as
how it renders Python code for what it does detect.     it is critical to
note that **autogenerate is not intended to be perfect**.   It is *always*
necessary to manually review and correct the **candidate migrations**
that autogenererate produces.   The feature is getting more and more
comprehensive and error-free as releases continue, but one should take
note of the current limitations.

Autogenerate **will detect**:

* Table additions, removals.
* Column additions, removals.
* Change of nullable status on columns.
* Basic changes in indexes and explcitly-named unique constraints

.. versionadded:: 0.6.1 Support for autogenerate of indexes and unique constraints.

* Basic changes in foreign key constraints

.. versionadded:: 0.7.1 Support for autogenerate of foreign key constraints.

Autogenerate can **optionally detect**:

* Change of column type.  This will occur if you set
  the :paramref:`.EnvironmentContext.configure.compare_type` parameter
  to ``True``, or to a custom callable function.   The default implementation
  **only detects major type changes**, such as between ``Numeric`` and
  ``String``, and does not detect changes in arguments such as lengths, precisions,
  or enumeration members.  The type comparison logic is extensible to work
  around these limitations, see :ref:`compare_types` for details.
* Change of server default.  This will occur if you set
  the :paramref:`.EnvironmentContext.configure.compare_server_default`
  parameter to ``True``, or to a custom callable function.
  This feature works well for simple cases but cannot always produce
  accurate results.  The Postgresql backend will actually invoke
  the "detected" and "metadata" values against the database to
  determine equivalence.  The feature is off by default so that
  it can be tested on the target schema first.  Like type comparison,
  it can also be customized by passing a callable; see the
  function's documentation for details.

Autogenerate **can not detect**:

* Changes of table name.   These will come out as an add/drop of two different
  tables, and should be hand-edited into a name change instead.
* Changes of column name.  Like table name changes, these are detected as
  a column add/drop pair, which is not at all the same as a name change.
* Anonymously named constraints.  Give your constraints a name,
  e.g. ``UniqueConstraint('col1', 'col2', name="my_name")``.  See the section
  :doc:`naming` for background on how to configure automatic naming schemes
  for constraints.
* Special SQLAlchemy types such as :class:`~sqlalchemy.types.Enum` when generated
  on a backend which doesn't support ENUM directly - this because the
  representation of such a type
  in the non-supporting database, i.e. a CHAR+ CHECK constraint, could be
  any kind of CHAR+CHECK.  For SQLAlchemy to determine that this is actually
  an ENUM would only be a guess, something that's generally a bad idea.
  To implement your own "guessing" function here, use the
  :meth:`sqlalchemy.events.DDLEvents.column_reflect` event
  to detect when a CHAR (or whatever the target type is) is reflected,
  and change it to an ENUM (or whatever type is desired) if it is known that
  that's the intent of the type.  The
  :meth:`sqlalchemy.events.DDLEvents.after_parent_attach`
  can be used within the autogenerate process to intercept and un-attach
  unwanted CHECK constraints.

Autogenerate can't currently, but **will eventually detect**:

* Some free-standing constraint additions and removals may not be supported,
  including PRIMARY KEY, EXCLUDE, CHECK; these are not necessarily implemented
  within the autogenerate detection system and also may not be supported by
  the supporting SQLAlchemy dialect.
* Sequence additions, removals - not yet implemented.

Autogenerating Multiple MetaData collections
--------------------------------------------

The ``target_metadata`` collection may also be defined as a sequence
if an application has multiple :class:`~sqlalchemy.schema.MetaData`
collections involved::

    from myapp.mymodel1 import Model1Base
    from myapp.mymodel2 import Model2Base
    target_metadata = [Model1Base.metadata, Model2Base.metadata]

The sequence of :class:`~sqlalchemy.schema.MetaData` collections will be
consulted in order during the autogenerate process.  Note that each
:class:`~sqlalchemy.schema.MetaData` must contain **unique** table keys
(e.g. the "key" is the combination of the table's name and schema);
if two :class:`~sqlalchemy.schema.MetaData` objects contain a table
with the same schema/name combination, an error is raised.

.. versionchanged:: 0.9.0 the
  :paramref:`.EnvironmentContext.configure.target_metadata`
  parameter may now be passed a sequence of
  :class:`~sqlalchemy.schema.MetaData` objects to support
  autogeneration of multiple :class:`~sqlalchemy.schema.MetaData`
  collections.

Comparing and Rendering Types
------------------------------

The area of autogenerate's behavior of comparing and rendering Python-based type objects
in migration scripts presents a challenge, in that there's
a very wide variety of types to be rendered in scripts, including those
part of SQLAlchemy as well as user-defined types.   A few options
are given to help out with this task.

.. _autogen_module_prefix:

Controlling the Module Prefix
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

When types are rendered, they are generated with a **module prefix**, so
that they are available based on a relatively small number of imports.
The rules for what the prefix is is based on the kind of datatype as well
as configurational settings.   For example, when Alembic renders SQLAlchemy
types, it will by default prefix the type name with the prefix ``sa.``::

    Column("my_column", sa.Integer())

The use of the ``sa.`` prefix is controllable by altering the value
of :paramref:`.EnvironmentContext.configure.sqlalchemy_module_prefix`::

    def run_migrations_online():
        # ...

        context.configure(
                    connection=connection,
                    target_metadata=target_metadata,
                    sqlalchemy_module_prefix="sqla.",
                    # ...
                    )

        # ...

In either case, the ``sa.`` prefix, or whatever prefix is desired, should
also be included in the imports section of ``script.py.mako``; it also
defaults to ``import sqlalchemy as sa``.


For user-defined types, that is, any custom type that
is not within the ``sqlalchemy.`` module namespace, by default Alembic will
use the **value of __module__ for the custom type**::

    Column("my_column", myapp.models.utils.types.MyCustomType())

The imports for the above type again must be made present within the migration,
either manually, or by adding it to ``script.py.mako``.

.. versionchanged:: 0.7.0
   The default module prefix rendering for a user-defined type now makes use
   of the type's ``__module__`` attribute to retrieve the prefix, rather than
   using the value of
   :paramref:`~.EnvironmentContext.configure.sqlalchemy_module_prefix`.


The above custom type has a long and cumbersome name based on the use
of ``__module__`` directly, which also implies that lots of imports would
be needed in order to accomodate lots of types.  For this reason, it is
recommended that user-defined types used in migration scripts be made
available from a single module.  Suppose we call it ``myapp.migration_types``::

    # myapp/migration_types.py

    from myapp.models.utils.types import MyCustomType

We can first add an import for ``migration_types`` to our ``script.py.mako``::

    from alembic import op
    import sqlalchemy as sa
    import myapp.migration_types
    ${imports if imports else ""}

We then override Alembic's use of ``__module__`` by providing a fixed
prefix, using the :paramref:`.EnvironmentContext.configure.user_module_prefix`
option::

    def run_migrations_online():
        # ...

        context.configure(
                    connection=connection,
                    target_metadata=target_metadata,
                    user_module_prefix="myapp.migration_types.",
                    # ...
                    )

        # ...

Above, we now would get a migration like::

  Column("my_column", myapp.migration_types.MyCustomType())

Now, when we inevitably refactor our application to move ``MyCustomType``
somewhere else, we only need modify the ``myapp.migration_types`` module,
instead of searching and replacing all instances within our migration scripts.

.. versionadded:: 0.6.3 Added :paramref:`.EnvironmentContext.configure.user_module_prefix`.

.. _autogen_render_types:

Affecting the Rendering of Types Themselves
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The methodology Alembic uses to generate SQLAlchemy and user-defined type constructs
as Python code is plain old ``__repr__()``.   SQLAlchemy's built-in types
for the most part have a ``__repr__()`` that faithfully renders a
Python-compatible constructor call, but there are some exceptions, particularly
in those cases when a constructor accepts arguments that aren't compatible
with ``__repr__()``, such as a pickling function.

When building a custom type that will be rendered into a migration script,
it is often necessary to explicitly give the type a ``__repr__()`` that will
faithfully reproduce the constructor for that type.   This, in combination
with :paramref:`.EnvironmentContext.configure.user_module_prefix`, is usually
enough.  However, if additional behaviors are needed, a more comprehensive
hook is the :paramref:`.EnvironmentContext.configure.render_item` option.
This hook allows one to provide a callable function within ``env.py`` that will fully take
over how a type is rendered, including its module prefix::

    def render_item(type_, obj, autogen_context):
        """Apply custom rendering for selected items."""

        if type_ == 'type' and isinstance(obj, MySpecialType):
            return "mypackage.%r" % obj

        # default rendering for other objects
        return False

    def run_migrations_online():
        # ...

        context.configure(
                    connection=connection,
                    target_metadata=target_metadata,
                    render_item=render_item,
                    # ...
                    )

        # ...

In the above example, we'd ensure our ``MySpecialType`` includes an appropriate
``__repr__()`` method, which is invoked when we call it against ``"%r"``.

The callable we use for :paramref:`.EnvironmentContext.configure.render_item`
can also add imports to our migration script.  The :class:`.AutogenContext` passed in
contains a datamember called :attr:`.AutogenContext.imports`, which is a Python
``set()`` for which we can add new imports.  For example, if ``MySpecialType``
were in a module called ``mymodel.types``, we can add the import for it
as we encounter the type::

    def render_item(type_, obj, autogen_context):
        """Apply custom rendering for selected items."""

        if type_ == 'type' and isinstance(obj, MySpecialType):
            # add import for this type
            autogen_context.imports.add("from mymodel import types")
            return "types.%r" % obj

        # default rendering for other objects
        return False

.. versionchanged:: 0.8 The ``autogen_context`` data member passed to
   the ``render_item`` callable is now an instance of :class:`.AutogenContext`.

.. versionchanged:: 0.8.3 The "imports" data member of the autogen context
   is restored to the new :class:`.AutogenContext` object as
   :attr:`.AutogenContext.imports`.

The finished migration script will include our imports where the
``${imports}`` expression is used, producing output such as::

  from alembic import op
  import sqlalchemy as sa
  from mymodel import types

  def upgrade():
      op.add_column('sometable', Column('mycolumn', types.MySpecialType()))


.. _compare_types:

Comparing Types
^^^^^^^^^^^^^^^^

The default type comparison logic will work for SQLAlchemy built in types as
well as basic user defined types.   This logic is only enabled if the
:paramref:`.EnvironmentContext.configure.compare_type` parameter
is set to True::

    context.configure(
        # ...
        compare_type = True
    )

.. note::

   The default type comparison logic (which is end-user extensible) currently
   works for **major changes in type only**, such as between ``Numeric`` and
   ``String``.     The logic will **not** detect changes such as:

   * changes between types that have the same "type affinity", such as
     between ``VARCHAR`` and ``TEXT``, or ``FLOAT`` and ``NUMERIC``

   * changes between the arguments within the type, such as the lengths of
     strings, precision values for numerics, the elements inside of an
     enumeration.

   Detection of these kinds of parameters is a long term project on the
   SQLAlchemy side.

Alternatively, the :paramref:`.EnvironmentContext.configure.compare_type`
parameter accepts a callable function which may be used to implement custom type
comparison logic, for cases such as where special user defined types
are being used::

    def my_compare_type(context, inspected_column,
                metadata_column, inspected_type, metadata_type):
        # return False if the metadata_type is the same as the inspected_type
        # or None to allow the default implementation to compare these
        # types. a return value of True means the two types do not
        # match and should result in a type change operation.
        return None

    context.configure(
        # ...
        compare_type = my_compare_type
    )

Above, ``inspected_column`` is a :class:`sqlalchemy.schema.Column` as
returned by
:meth:`sqlalchemy.engine.reflection.Inspector.reflecttable`, whereas
``metadata_column`` is a :class:`sqlalchemy.schema.Column` from the
local model environment.  A return value of ``None`` indicates that default
type comparison to proceed.

Additionally, custom types that are part of imported or third party
packages which have special behaviors such as per-dialect behavior
should implement a method called ``compare_against_backend()``
on their SQLAlchemy type.   If this method is present, it will be called
where it can also return True or False to specify the types compare as
equivalent or not; if it returns None, default type comparison logic
will proceed::

    class MySpecialType(TypeDecorator):

        # ...

        def compare_against_backend(self, dialect, conn_type):
            # return True if this type is the same as the given database type,
            # or None to allow the default implementation to compare these
            # types. a return value of False means the given type does not
            # match this type.

            if dialect.name == 'postgresql':
                return isinstance(conn_type, postgresql.UUID)
            else:
                return isinstance(conn_type, String)

.. warning::

    The boolean return values for the above
    ``compare_against_backend`` method, which is part of SQLAlchemy and not
    Alembic,are **the opposite** of that of the
    :paramref:`.EnvironmentContext.configure.compare_type` callable, returning
    ``True`` for types that are the same vs. ``False`` for types that are
    different.The :paramref:`.EnvironmentContext.configure.compare_type`
    callable on the other hand should return ``True`` for types that are
    **different**.

The order of precedence regarding the
:paramref:`.EnvironmentContext.configure.compare_type` callable vs. the
type itself implementing ``compare_against_backend`` is that the
:paramref:`.EnvironmentContext.configure.compare_type` callable is favored
first; if it returns ``None``, then the ``compare_against_backend`` method
will be used, if present on the metadata type.  If that returns ``None``,
then a basic check for type equivalence is run.

.. versionadded:: 0.7.6 - added support for the ``compare_against_backend()``
   method.



