import { useEffect, useState } from "react";
import { useAuth } from "../contexts/AuthContext";
import { api } from "../lib/api";
import { Card } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Switch } from "../components/ui/switch";
import Spinner from "../components/Spinner";
import type { UserSettings } from "../types/settings";

const DEFAULT_SETTINGS: UserSettings = {
  iflowUrl: "https://app.hriflow.ro/#/dashboard",
  iflowUsername: "",
  iflowPassword: "",
  iflowHeadless: true,
  iflowTimeout: 30000,
};

export default function Settings() {
  const { user } = useAuth();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [testResult, setTestResult] = useState<string | null>(null);
  const [settings, setSettings] = useState<UserSettings>(DEFAULT_SETTINGS);
  const [hasCredentials, setHasCredentials] = useState(false);

  useEffect(() => {
    loadSettings();
  }, []);

  async function loadSettings() {
    setLoading(true);
    setError(null);
    try {
      const loadedSettings = await api.getSettings();
      setSettings({ ...DEFAULT_SETTINGS, ...loadedSettings });
      // Check if credentials exist
      const hasCreds = !!(loadedSettings.iflowUsername && loadedSettings.iflowPassword);
      setHasCredentials(hasCreds);
    } catch (e) {
      const errorMessage = e instanceof Error ? e.message : "Failed to load settings";
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  }

  async function handleSave() {
    setSaving(true);
    setError(null);
    setSuccess(null);
    setTestResult(null);
    try {
      await api.updateSettings(settings);
      setSuccess("Settings saved successfully");
      const hasCreds = !!(settings.iflowUsername && settings.iflowPassword);
      setHasCredentials(hasCreds);
    } catch (e) {
      const errorMessage = e instanceof Error ? e.message : "Failed to save settings";
      setError(errorMessage);
    } finally {
      setSaving(false);
    }
  }

  async function handleTest() {
    setTesting(true);
    setError(null);
    setSuccess(null);
    setTestResult(null);
    try {
      const result = await api.testCredentials();
      if (result.success) {
        setTestResult("Connection successful! Credentials are valid.");
      } else {
        setTestResult(`Test failed: ${result.message || "Unknown error"}`);
      }
    } catch (e) {
      const errorMessage = e instanceof Error ? e.message : "Failed to test credentials";
      setTestResult(`Test failed: ${errorMessage}`);
    } finally {
      setTesting(false);
    }
  }

  async function handleDelete() {
    if (!confirm("Are you sure you want to delete your iFlow credentials?")) {
      return;
    }
    setDeleting(true);
    setError(null);
    setSuccess(null);
    setTestResult(null);
    try {
      await api.deleteCredentials();
      setSettings(DEFAULT_SETTINGS);
      setHasCredentials(false);
      setSuccess("Credentials deleted successfully");
    } catch (e) {
      const errorMessage = e instanceof Error ? e.message : "Failed to delete credentials";
      setError(errorMessage);
    } finally {
      setDeleting(false);
    }
  }

  function updateSetting<K extends keyof UserSettings>(
    field: K,
    value: UserSettings[K]
  ) {
    setSettings({ ...settings, [field]: value });
  }

  if (loading) {
    return (
      <div className="p-6">
        <Spinner />
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold">Settings</h1>

      {/* User Info Card */}
      <Card className="p-4">
        <h2 className="text-base font-semibold mb-2">Account</h2>
        <p className="text-sm">
          Logged in as <span className="font-medium">{user?.email}</span>
        </p>
      </Card>

      {/* iFlow Credentials Card */}
      <Card className="p-4">
        <h2 className="text-base font-semibold mb-4">iFlow Credentials</h2>

        {error && (
          <div className="mb-4 rounded-md bg-red-50 p-3 text-sm text-red-700">
            {error}
          </div>
        )}

        {success && (
          <div className="mb-4 rounded-md bg-green-50 p-3 text-sm text-green-700">
            {success}
          </div>
        )}

        {testResult && (
          <div
            className={`mb-4 rounded-md p-3 text-sm ${
              testResult.includes("successful")
                ? "bg-green-50 text-green-700"
                : "bg-yellow-50 text-yellow-700"
            }`}
          >
            {testResult}
          </div>
        )}

        <div className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="iflow-url">iFlow URL</Label>
            <Input
              id="iflow-url"
              type="url"
              placeholder="https://app.hriflow.ro/#/dashboard"
              value={settings.iflowUrl || ""}
              onChange={(e) => updateSetting("iflowUrl", e.target.value)}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="iflow-username">Username</Label>
            <Input
              id="iflow-username"
              type="text"
              placeholder="your.username@company.com"
              value={settings.iflowUsername || ""}
              onChange={(e) => updateSetting("iflowUsername", e.target.value)}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="iflow-password">Password</Label>
            <Input
              id="iflow-password"
              type="password"
              placeholder="Enter password"
              value={settings.iflowPassword || ""}
              onChange={(e) => updateSetting("iflowPassword", e.target.value)}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="timeout">Timeout (ms)</Label>
            <Input
              id="timeout"
              type="number"
              min="5000"
              max="120000"
              step="1000"
              value={settings.iflowTimeout || 30000}
              onChange={(e) => updateSetting("iflowTimeout", parseInt(e.target.value, 10))}
            />
            <p className="text-xs text-gray-500">
              Timeout for browser operations (5000-120000ms)
            </p>
          </div>

          <div className="flex items-center space-x-2">
            <Switch
              id="headless"
              checked={settings.iflowHeadless ?? true}
              onCheckedChange={(checked) => updateSetting("iflowHeadless", checked)}
            />
            <Label htmlFor="headless" className="cursor-pointer">
              Headless mode (run browser in background)
            </Label>
          </div>

          <div className="flex gap-2 pt-2">
            <Button onClick={handleSave} disabled={saving || deleting || testing}>
              {saving ? "Saving..." : "Save"}
            </Button>
            <Button
              variant="secondary"
              onClick={handleTest}
              disabled={!hasCredentials || saving || deleting || testing}
            >
              {testing ? "Testing..." : "Test Connection"}
            </Button>
            {hasCredentials && (
              <Button
                variant="destructive"
                onClick={handleDelete}
                disabled={saving || deleting || testing}
              >
                {deleting ? "Deleting..." : "Delete Credentials"}
              </Button>
            )}
          </div>
        </div>
      </Card>
    </div>
  );
}
