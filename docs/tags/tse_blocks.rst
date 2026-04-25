======================
TagScriptEngine Blocks
======================

-----------
Core Blocks
-----------

^^^^^^^^^^^^^^^^
Assignment Block
^^^^^^^^^^^^^^^^

.. autoclass:: TagScriptEngine.AssignmentBlock

^^^^^^^^^^^
Cycle Block
^^^^^^^^^^^

.. autoclass:: TagScriptEngine.CycleBlock

^^^^^^^^^^
List Block
^^^^^^^^^^

.. autoclass:: TagScriptEngine.ListBlock

^^^^^^^^^^^^
Random Block
^^^^^^^^^^^^

.. autoclass:: TagScriptEngine.RandomBlock

^^^^^^^^^^
Math Block
^^^^^^^^^^

.. autoclass:: TagScriptEngine.MathBlock

^^^^^^^^^^^
Range Block
^^^^^^^^^^^

.. autoclass:: TagScriptEngine.RangeBlock

--------------
Control Blocks
--------------

^^^^^^^^
If Block
^^^^^^^^

.. autoclass:: TagScriptEngine.IfBlock

^^^^^^^^^^^
Break Block
^^^^^^^^^^^

.. autoclass:: TagScriptEngine.BreakBlock

^^^^^^^^^
All Block
^^^^^^^^^

.. autoclass:: TagScriptEngine.AllBlock

^^^^^^^^^
Any Block
^^^^^^^^^

.. autoclass:: TagScriptEngine.AnyBlock

^^^^^^^^^^^^^^^^^
Fifty-fifty Block
^^^^^^^^^^^^^^^^^

.. autoclass:: TagScriptEngine.FiftyFiftyBlock

^^^^^^^^^^
Stop Block
^^^^^^^^^^

.. autoclass:: TagScriptEngine.StopBlock

-------------
String Blocks
-------------

^^^^^^^^^^
Join Block
^^^^^^^^^^

.. autoclass:: TagScriptEngine.JoinBlock

^^^^^^^^^^^^^^^
Replace Block
^^^^^^^^^^^^^^^

.. autoclass:: TagScriptEngine.ReplaceBlock

^^^^^^^^^^^^^^^
URLEncode Block
^^^^^^^^^^^^^^^

.. autoclass:: TagScriptEngine.URLEncodeBlock

-------------
Search Blocks
-------------

^^^^^^^^
In Block
^^^^^^^^

    The ``in`` block checks if the parameter string is anywhere in the payload as a substring.

    **Usage:** ``{in(<string>):<payload>}``

    **Aliases:** ``None``

    **Payload:** payload

    **Parameter:** string

    **Examples:** ::

        {in(apple pie):banana pie apple pie and other pie}
        # true
        {in(mute):How does it feel to be muted?}
        # true
        {in(a):How does it feel to be muted?}
        # false

^^^^^^^^^^^^^^
Contains Block
^^^^^^^^^^^^^^

    The ``contains`` block strictly checks if the parameter is in the payload,
    split by whitespace. This performs **exact** matching on whitespace-split words.
    For example, ``food`` will **not** match ``food.`` (with trailing punctuation).

    **Usage:** ``{contains(<string>):<payload>}``

    **Aliases:** ``None``

    **Payload:** payload

    **Parameter:** string

    **Examples:** ::

        {contains(mute):How does it feel to be muted?}
        # false
        {contains(muted?):How does it feel to be muted?}
        # true

^^^^^^^^^^^
Index Block
^^^^^^^^^^^

    The ``index`` block finds the location/index of the parameter in the payload,
    split by whitespace. If the parameter string is not found, it returns ``-1``.
    This performs **exact** matching on whitespace-split words.

    **Usage:** ``{index(<string>):<payload>}``

    **Aliases:** ``None``

    **Payload:** payload

    **Parameter:** string

    **Examples:** ::

        {index(food):I love to eat food. everyone does.}
        # -1 # because of the period. "food" != "food."
        {index(food):I love to eat food everyone does}
        # 4 # because "food" is the 4th word in the payload
        {index(love):I love to eat food}
        # 1 # because "love" is the 2nd word in the payload
        {index(pie):I love to eat food}
        # -1 # because "pie" is not in the payload

--------------------
Miscellaneous Blocks
--------------------

^^^^^^^^^^^^^
Ordinal Block
^^^^^^^^^^^^^

.. autoclass:: TagScriptEngine.OrdinalBlock

^^^^^^^^^^^^^^
Strftime Block
^^^^^^^^^^^^^^

.. autoclass:: TagScriptEngine.StrfBlock

^^^^^^^^^^^^^^^
Substring Block
^^^^^^^^^^^^^^^

.. autoclass:: TagScriptEngine.SubstringBlock

-----------------
Case Blocks
-----------------

^^^^^^^^^^^
Upper Block
^^^^^^^^^^^

.. autoclass:: TagScriptEngine.UpperBlock

^^^^^^^^^^^
Lower Block
^^^^^^^^^^^

.. autoclass:: TagScriptEngine.LowerBlock

-----------------
Counting Blocks
-----------------

^^^^^^^^^^^
Count Block
^^^^^^^^^^^

.. autoclass:: TagScriptEngine.CountBlock

^^^^^^^^^^^^
Length Block
^^^^^^^^^^^^

.. autoclass:: TagScriptEngine.LengthBlock
