/**
 * AWX MCP VS Code Extension
 * 
 * This extension integrates AWX with GitHub Copilot through the Model Context Protocol (MCP).
 * It runs a local MCP server and registers it with GitHub Copilot Chat.
 * 
 * The extension is modularized for maintainability:
 * - extension/dependencies.ts: Dependency checking and setup
 * - extension/mcpConfiguration.ts: MCP server configuration for Copilot
 * - extension/htmlGenerators.ts: Webview HTML generation
 * - extension/pythonExecutor.ts: Python command execution
 * - extension/commands.ts: Command registration
 * - mcp/*: MCP server lifecycle management
 *
 * Tool access is provided natively: the extension registers the MCP server with
 * Copilot (see extension/mcpConfiguration.ts), and Copilot/agent mode calls the
 * server's tools directly over MCP.
 */

import * as vscode from 'vscode';
import { MCPServerManager } from './mcpServerManager';
import { ConfigurationProvider } from './views/configurationProvider';
import { ConfigurationWebview } from './views/configurationWebview';
import { ConnectionStatusProvider } from './views/connectionStatusProvider';
import { MetricsProvider } from './views/metricsProvider';
import { LogsProvider } from './views/logsProvider';
import { registerCommands } from './extension/commands';
import { checkDependencies, setupDependencies } from './extension/dependencies';
import { configureMcpServer } from './extension/mcpConfiguration';

let serverManager: MCPServerManager;
let statusBarItem: vscode.StatusBarItem;
let outputChannel: vscode.OutputChannel;
let configProvider: ConfigurationProvider;
let configWebview: ConfigurationWebview;
let connectionStatusProvider: ConnectionStatusProvider;

export function activate(context: vscode.ExtensionContext) {
    console.log('AWX MCP extension is now active');

    // Create output channel
    outputChannel = vscode.window.createOutputChannel('AWX MCP');
    context.subscriptions.push(outputChannel);

    // Create status bar item
    statusBarItem = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Right, 100);
    statusBarItem.command = 'awx-mcp.status';
    statusBarItem.text = '$(plug) AWX MCP';
    statusBarItem.tooltip = 'AWX MCP Server for GitHub Copilot';
    statusBarItem.show();
    context.subscriptions.push(statusBarItem);

    // Check dependencies before configuring MCP
    checkDependencies(outputChannel).then(success => {
        if (success) {
            // Configure MCP server for Copilot Chat only if dependencies are ready
            configureMcpServer(outputChannel).catch(err => {
                outputChannel.appendLine(`Warning: Could not configure MCP server: ${err.message}`);
            });
        } else {
            statusBarItem.text = '$(warning) AWX MCP: Setup Required';
            statusBarItem.tooltip = 'Click to setup AWX MCP dependencies';
            vscode.window.showWarningMessage(
                'AWX MCP requires Python dependencies. Click "Setup Now" to install.',
                'Setup Now',
                'View Requirements',
                'Dismiss'
            ).then(selection => {
                if (selection === 'Setup Now') {
                    vscode.commands.executeCommand('awx-mcp.setupDependencies');
                } else if (selection === 'View Requirements') {
                    outputChannel.show();
                }
            });
        }
    });

    // Initialize server manager (for manual control)
    serverManager = new MCPServerManager(context, outputChannel, statusBarItem);

    // Initialize configuration provider
    configProvider = new ConfigurationProvider(context);
    vscode.window.registerTreeDataProvider('awx-mcp-instances', configProvider);

    // Initialize configuration webview
    configWebview = new ConfigurationWebview(context, configProvider);

    // Initialize connection status provider
    connectionStatusProvider = new ConnectionStatusProvider(configProvider, context, outputChannel);
    vscode.window.registerTreeDataProvider('awx-mcp-connection-status', connectionStatusProvider);

    // Register metrics and logs providers
    const metricsProvider = new MetricsProvider(serverManager);
    vscode.window.registerTreeDataProvider('awx-mcp-metrics', metricsProvider);

    const logsProvider = new LogsProvider(serverManager);
    vscode.window.registerTreeDataProvider('awx-mcp-logs', logsProvider);

    // Tool access is native: once the MCP server is registered (above), Copilot
    // and agent mode call its tools directly over MCP — no custom chat
    // participant is needed.
    outputChannel.appendLine('✓ AWX MCP server registered; use the tools via Copilot / agent mode');

    // Register all commands (modularized in extension/commands.ts)
    registerCommands(
        context,
        serverManager,
        configProvider,
        configWebview,
        connectionStatusProvider,
        outputChannel
    );
}

export function deactivate() {
    if (serverManager) {
        serverManager.stop();
    }
}
