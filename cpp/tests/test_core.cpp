#include <gtest/gtest.h>

#include "forge_cpp/core.hpp"

// forge_cpp_tests: GoogleTest native unit tests (§38, §254). Week 1 scaffold: proves
// the native test target and CMake preset wiring work before real parser/aggregator
// tests exist.

TEST(ForgeCoreScaffold, AddIsCorrect) {
  EXPECT_EQ(forge::core::add(2, 3), 5);
}

TEST(ForgeCoreScaffold, AddHandlesNegatives) {
  EXPECT_EQ(forge::core::add(-2, 2), 0);
}
