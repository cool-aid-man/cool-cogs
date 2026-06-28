.. role:: python(code)
    :language: python

=================
Default Variables
=================

The following blocks will be present and accessable as defaults when running any tag.

--------------
Meta Variables
--------------

Meta variables reference meta attributes about the tag invocation.

^^^^^^^^^^
Args Block
^^^^^^^^^^

.. autoclass:: TagScriptEngine.StringAdapter

    The ``{args}`` block represents the arguments passed after the tag name when invoking
    a tag. If no parameter is passed, it returns all the text after the invocation name.
    If an index is passed, it will split the arguments into a list by the given splitter,
    and return the word at that index. The default splitter is a " ".

    **Usage:** ``{args([index]):[splitter]>}``

    **Payload:** splitter

    **Parameter:** index

    **Examples:**

    In the following examples, assume the tag's name is ``argstag`` and the message
    content is ``[p]argstag My dog is cute! Would you like to see a photo?``. ::

        {args}
        # My dog is cute! Would you like to see a photo?

        {args(1)}
        # My

        {args(2):!}
        # Would you like to see a photo?

^^^^^^^^^^
Uses Block
^^^^^^^^^^

.. autoclass:: TagScriptEngine.IntAdapter

    The ``{uses}`` block returns the number of times a tag has been used.

    **Usage:** ``{uses}``

    **Payload:** None

    **Parameter:** None

    **Examples:** ::

        {uses}
        # 1

------------------------
Discord Object Variables
------------------------

These blocks reference Discord objects from the tag invocation context.

^^^^^^^^^^^^
Author Block
^^^^^^^^^^^^

.. autoclass:: TagScriptEngine.MemberAdapter

^^^^^^^^^^^^
Target Block
^^^^^^^^^^^^

    The ``{target}`` block follows the same usage and has the same attributes as the
    :ref:`Author Block`, but it resolves the target as follows:

    - the first user **@mentioned** in the tag invocation message, if any; otherwise
    - the first raw **user ID** in the tag's arguments, as long as that ID belongs to
      a **member of the current server** (resolved from cache); otherwise
    - the tag author.

    Only the first match is used in each case; any further mentions or IDs are
    ignored. An ID that is not a member of the server falls back to the tag author.

    **Usage:** ``{target}``

    **Aliases:** ``{member}``

^^^^^^^^^^^^^
Channel Block
^^^^^^^^^^^^^

.. autoclass:: TagScriptEngine.ChannelAdapter

^^^^^^^^^^^^
Server Block
^^^^^^^^^^^^

.. autoclass:: TagScriptEngine.GuildAdapter

^^^^^^^^^
Bot Block
^^^^^^^^^

.. autoclass:: TagScriptEngine.RedBotAdapter

.. warning::
    Attributes marked ``(*)`` are owner-only: they are only available when the
    tag is invoked by a bot owner, and return nothing for everyone else.
