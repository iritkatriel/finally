# `return` in `finally` considered harmful

### Abstract

The semantics of `return`, `break` and `continue` in a `finally` block are
surprising. This document describes an analysis of their use in real code
(popular PyPI packages) which was condicted in order to assess the feasibility
of blocking these features. The results show that

1. These patterns are not used often.
2. When they are used, they are usually used incorrectly, leading to unintended
   swallowing of exceptions.
3. Code authors are overwhelmingly receptive and quick to fix the code when
   the error is pointed out to them.

## Introduction


