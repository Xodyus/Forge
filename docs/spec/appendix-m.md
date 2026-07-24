# Appendix M - References and Further Study

## 429. Target-Role Context

\[HRT-1\] Hudson River Trading, "Software Engineering Internship --- C++ or Python --- Summer 2027." https://www.hudsonrivertrading.com/hrt-job/software-engineering-internship-c-or-python-summer-2027/

\[HRT-2\] Hudson River Trading, "Interviewing at HRT." https://www.hudsonrivertrading.com/hrtbeat/interview-at-hrt/

\[HRT-3\] Hudson River Trading, "Intern Spotlight: Software Engineering Summer Projects." https://www.hudsonrivertrading.com/hrtbeat/intern-spotlight-software-engineering-summer-projects/

\[HRT-4\] Hudson River Trading, "Student Opportunities." https://www.hudsonrivertrading.com/student-opportunities/

These sources motivate the target engineering signals and recruiting context only. Forge is an independent educational design and does not describe HRT proprietary systems.

## 430. Python and Standard-Library References

- Python documentation: https://docs.python.org/3/
- asyncio: https://docs.python.org/3/library/asyncio.html
- multiprocessing: https://docs.python.org/3/library/multiprocessing.html
- shared memory: https://docs.python.org/3/library/multiprocessing.shared_memory.html
- sqlite3: https://docs.python.org/3/library/sqlite3.html
- mmap: https://docs.python.org/3/library/mmap.html
- signal: https://docs.python.org/3/library/signal.html
- struct: https://docs.python.org/3/library/struct.html
- hashlib: https://docs.python.org/3/library/hashlib.html
- resource: https://docs.python.org/3/library/resource.html

## 431. C++, Build, and Binding References

- C++ language reference: https://en.cppreference.com/w/cpp
- pybind11 documentation: https://pybind11.readthedocs.io/
- CMake documentation: https://cmake.org/documentation/
- scikit-build-core documentation: https://scikit-build-core.readthedocs.io/
- GoogleTest documentation: https://google.github.io/googletest/
- Clang AddressSanitizer: https://clang.llvm.org/docs/AddressSanitizer.html
- Clang UndefinedBehaviorSanitizer: https://clang.llvm.org/docs/UndefinedBehaviorSanitizer.html
- LLVM libFuzzer: https://llvm.org/docs/LibFuzzer.html

## 432. SQLite and Linux Systems References

- SQLite documentation: https://www.sqlite.org/docs.html
- SQLite WAL mode: https://www.sqlite.org/wal.html
- SQLite transactions: https://www.sqlite.org/lang_transaction.html
- SQLite online backup API: https://www.sqlite.org/backup.html
- Linux man-pages project: https://man7.org/linux/man-pages/
- epoll(7): https://man7.org/linux/man-pages/man7/epoll.7.html
- unix(7): https://man7.org/linux/man-pages/man7/unix.7.html
- socket(7): https://man7.org/linux/man-pages/man7/socket.7.html
- mmap(2): https://man7.org/linux/man-pages/man2/mmap.2.html
- fsync(2): https://man7.org/linux/man-pages/man2/fsync.2.html
- rename(2): https://man7.org/linux/man-pages/man2/rename.2.html
- signal(7): https://man7.org/linux/man-pages/man7/signal.7.html
- proc(5): https://man7.org/linux/man-pages/man5/proc.5.html

## 433. Testing, Quality, and Measurement References

- pytest documentation: https://docs.pytest.org/
- Hypothesis documentation: https://hypothesis.readthedocs.io/
- Ruff documentation: https://docs.astral.sh/ruff/
- mypy documentation: https://mypy.readthedocs.io/
- Python Packaging User Guide: https://packaging.python.org/
- Linux perf wiki and documentation: https://perf.wiki.kernel.org/
- Google Benchmark documentation: https://google.github.io/benchmark/

## 434. Conceptual Reading Topics

Beyond tool documentation, the project benefits from careful study of leases and fencing, idempotency, transaction isolation, write-ahead logging, crash consistency, process supervision, stream framing, flow control, deterministic replay, property-based testing, model-based testing, queueing and parallel scaling, profiling, and experimental design. When incorporating a specific paper, book, or article into the repository, cite the exact edition or URL and distinguish its concepts from Forge's original implementation decisions.

# Closing Engineering Standard

Forge succeeds when its smallest truthful description is also technically interesting: an immutable event dataset is divided deterministically; a durable coordinator leases logical tasks to process-isolated workers; attempts may duplicate after failure; each output is staged under its attempt identity; a fencing epoch and conditional transaction select one visible result; restart recovery uses durable evidence rather than memory; a narrow C++ boundary is justified by profile and verified against a Python oracle; and every public claim can be regenerated from a tagged release.

The project should be built in that order. Define the guarantee. Preserve the reference. Bound the resources. Inject the failure. Observe the state. Measure the bottleneck. Publish the evidence. State the limitation. That sequence is the master design.
