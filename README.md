# Horus

Horus is a Python desktop application (built with Tkinter) that integrates [OpenWork](https://github.com/different-ai/openwork) to automatically generate and execute end-to-end (E2E) Playwright tests for your projects.

Simply select a project folder via the user interface, and Horus will use the local OpenWork AI orchestrator to inspect the folder, write Playwright tests, and run them, displaying the live results in the UI.

## Prerequisites

- **Python 3.10+** (with Tkinter support)
- **Node.js** (v18+ recommended)
- **pnpm** and **npm**

## Installation

1. **Clone the repository with submodules:**
   ```bash
   git clone --recurse-submodules https://github.com/yash-nullaxis/horus.git
   cd horus
   ```
   *(If you've already cloned it without submodules, run `git submodule update --init --recursive`)*

2. **Install Node dependencies:**
   ```bash
   npm install
   ```

3. **Install OpenWork Orchestrator dependencies:**
   ```bash
   cd openwork
   pnpm install
   cd ..
   ```

## Usage

Run the desktop application using Python:

```bash
python horus.py
```

1. Click the **Select Folder & Generate/Run Tests** button.
2. Choose a project directory on your machine.
3. Horus will launch the OpenWork AI agent in the background. The agent will generate E2E tests using Playwright.
4. Once generation is complete, Horus automatically triggers the tests (`npx playwright test` or `pytest`) and streams the test results into the application window.
