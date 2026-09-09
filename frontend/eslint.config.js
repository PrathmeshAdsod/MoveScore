// eslint.config.js — flat config (CommonJS)
const { FlatCompat } = require("@eslint/eslintrc");
const path = require("path");

const compat = new FlatCompat({
  baseDirectory: __dirname || path.resolve(),
});

/** @type {import('eslint').Linter.FlatConfig[]} */
const config = [
  ...compat.extends("next/core-web-vitals", "next/typescript"),
];

module.exports = config;
