#!/usr/bin/env bash
# Build a deployment zip for the SQS notification Lambda consumer (Week 6 Day 36).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BUILD_DIR="$ROOT/build/lambda"
OUTPUT_ZIP="$ROOT/dist/lambda_notification_consumer.zip"

if [[ -x "$ROOT/.venv/bin/pip" ]]; then
  PIP="$ROOT/.venv/bin/pip"
else
  PIP="pip"
fi

rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR" "$ROOT/dist"

echo "==> Installing Lambda dependencies into $BUILD_DIR"
"$PIP" install -r "$ROOT/requirements-lambda.txt" -t "$BUILD_DIR" --upgrade \
  --platform manylinux2014_x86_64 \
  --implementation cp \
  --python-version 3.12 \
  --only-binary=:all:

echo "==> Copying application package"
cp -R "$ROOT/app" "$BUILD_DIR/app"

echo "==> Creating zip archive"
(
  cd "$BUILD_DIR"
  find . -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true
  zip -r "$OUTPUT_ZIP" . -x '*.pyc' -x '*__pycache__*' >/dev/null
)

echo "==> Built $OUTPUT_ZIP ($(du -h "$OUTPUT_ZIP" | awk '{print $1}'))"
echo "Handler: app.lambda_handlers.sqs_notification_handler.handle_sqs_event"
echo "Runtime: Python 3.12"
