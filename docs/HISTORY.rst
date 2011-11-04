Changelog
=========

0.3.1 - Released (2011-09-19)
-----------------------------

* Raw code wrapper need to be updated to not render.

0.3 - Released (2011-08-17)
---------------------------

* Updated import location for pmr2.app-0.4.

0.2 - Released (2011-04-11)
---------------------------

* Math rendering for CellML 1.1, make use of the CellML API.
* Use MathJAX for cross browser math rendering.
* Updated import location to pmr2.app-0.4
* Included other CellML specific parts that got removed fom pmr2.app.

0.1.1 - Released (2010-07-05)
-----------------------------

* Fixed handling of null values in fields which were never present
  before.

0.1 - Released (2010-06-21)
---------------------------

* Extracted all CellML related functionality found in pmr2.app into this
  package.
* Merged functions provided in pmr2.processor.cmeta into this package.
* Keywords and other metadata no longer depends on the presence of 
  citations for the Cmeta annotations.
* Updated code generation, now generates CellML 1.1 code using the 
  cellml.api.simple package.  
* Also no longer deadlocks server process due to the usage of fork 
  (workaround of the select syscall locking issue by the API).
* Rendering of generated code uses shjs for highlighting.
* Various OpenCell specific views added.  Merged the launch via OpenCell
  link into the session link (i.e. when no session file is specified,
  the CellML file will be launched via that link instead).