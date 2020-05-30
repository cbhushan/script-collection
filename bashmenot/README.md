_bashmenot_
===========================================

_bashmenot_ is a library of [GNU _bash_](https://gnu.org/software/bash/) functions, used by [Halcyon](https://halcyon.sh/) and [Haskell on Heroku](https://haskellonheroku.com/).

This is a copy of [original _bashmenot_ library](https://github.com/mietek/bashmenot), which is no longer maintained.

Usage
-----

```
$ source bashmenot/src.sh
```

- See the [_bashmenot_ reference](https://cbhushan.github.io/bashmenot-website/pages/reference/) for a complete list of available functions and options.

- Read the [_bashmenot_ source code](./src) to understand how it works.


#### Dependencies

_bashmenot_ is written in [GNU _bash_](https://gnu.org/software/bash/), and requires:

- [GNU _date_](https://gnu.org/software/coreutils/manual/html_node/date-invocation.html) — for date formatting
- [GNU _sort_](https://gnu.org/software/coreutils/manual/html_node/sort-invocation.html) — for sorting
- [_curl_](http://curl.haxx.se/) — for remote storage
- [OpenSSL](https://openssl.org/) — for hashing and Amazon S3 storage
- [_git_](http://git-scm.com/) — for self-updates


About
-----

Originally made by [Miëtek Bak](https://mietek.io/).  Published under the BSD license.
