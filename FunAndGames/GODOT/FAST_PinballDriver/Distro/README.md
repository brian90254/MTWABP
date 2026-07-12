# FastHardwareRuntime — Godot plugin

A compiled C# runtime library of FAST Pinball hardware classes (Node3D-derived) for **Godot 4.1
.NET / C# projects**, built with `Godot.NET.Sdk/4.1.1` targeting `net6.0`.

This release ships one package per operating system. Each package is identical except for a single
file: the native serial-port shim for that OS. **If you export your game to an OS other than the one
you develop on, read section 4 before anything else.**

## 1. Which zip do I download?

Download the single package that matches **your development machine's OS**:

- `FastHardwareRuntime-windows.zip`
- `FastHardwareRuntime-linux.zip`
- `FastHardwareRuntime-macos.zip`

You do **not** need all three — exporting to a different OS is handled in section 4.

## 2. Requirements

- A Godot **4.1.x** project with **.NET / C# support** (the C# / "Mono" editor build). This is a
  compiled C# assembly; it will not load in a GDScript-only build of Godot.
- Your project is a C# project (it has a `.csproj`).

## 3. Install

1. Unzip the package into your Godot project root so the plugin lands at:

   ```
   <your project>/addons/FastHardwareRuntime/
   ```

2. Reference it from your project's `.csproj` (add the `<ItemGroup>` if you don't have one):

   ```xml
   <ItemGroup>
     <Reference Include="FastHardwareRuntime">
       <HintPath>addons/FastHardwareRuntime/FastHardwareRuntime.dll</HintPath>
       <Private>true</Private>
     </Reference>
     <PackageReference Include="System.IO.Ports" Version="7.0.0" />
   </ItemGroup>
   ```

   The `System.IO.Ports` line matters for exporting — see section 4.

3. Build: press **Build** in the Godot editor (or run `dotnet build`).

4. The `FAST_Pinball` types are now available — e.g. add a `FAST` node to a scene, or use the
   classes from your C# scripts.

## 4. Serial hardware, exported games & cross-OS export — read this

FAST hardware talks over a serial port, which is an operating-system operation. That splits your
dependency into two parts:

- **`FastHardwareRuntime.dll` and `System.IO.Ports.dll` are pure IL** — byte-for-byte identical on
  every OS, and Godot carries them into every export automatically. Nothing to manage.
- **The serial *native* shim is per-OS.** `System.IO.Ports` needs a small native library on Linux
  (`libSystem.IO.Ports.Native.so`) and macOS (`libSystem.IO.Ports.Native.dylib`). Windows needs
  none — it calls the Win32 API directly.

**The reliable rule: keep the `System.IO.Ports` `<PackageReference>` from step 3 in your project.**
With it, when you export to *any* OS the .NET build automatically ships the correct native shim for
that target — including when your development OS and your export OS differ. `System.IO.Ports` is a
standard Microsoft package on nuget.org; using it is normal .NET practice and does not tie you to how
this plugin itself is distributed.

| You develop on | You export to        | What you need to do                                        |
|----------------|----------------------|------------------------------------------------------------|
| Any OS         | The same OS          | Nothing extra — works as installed.                        |
| Windows        | Linux and/or macOS   | Nothing extra, **if** you kept the `System.IO.Ports` ref.  |
| Linux          | Windows and/or macOS | Same — the reference ships the right shim per target.      |
| macOS          | Windows and/or Linux | Same.                                                      |

> **Why not just hand-copy the `.so` / `.dylib`?** The native shim bundled in this zip is a
> convenience so serial works when you **run from the Godot editor on your development OS**. It is a
> loose file, so Godot does **not** reliably place it into an *exported* game (loose files are packed
> into the `.pck`, not left next to the executable where native loading looks). For exported and
> cross-OS builds, the `System.IO.Ports` `<PackageReference>` is what guarantees the right native is
> shipped. If you truly cannot use NuGet, you must manually place the target OS's shim next to the
> exported executable and test on that OS — not recommended.

## 5. Upgrading (delete & replace)

1. Delete the `addons/FastHardwareRuntime/` folder.
2. Unzip the new release into the same location.

Your `.csproj` reference points at a fixed path, so no project edits are needed. Rebuild.

## 6. What's in this package

- `FastHardwareRuntime.dll` — the plugin (pure cross-platform IL).
- `System.IO.Ports.dll` — managed serial API (convenience copy; the `<PackageReference>` is what
  actually drives export).
- The native serial shim for this package's OS (Linux `.so` / macOS `.dylib`; none on Windows) —
  for running from the editor on your dev OS.
- `GodotSharp` is intentionally **not** included; the Godot runtime supplies it.

## 7. Troubleshooting

- **`DllNotFoundException: System.IO.Ports.Native` in an exported game** → you're missing the
  `System.IO.Ports` `<PackageReference>`. Add it (step 3) and re-export.
- **`The type or namespace name 'FAST_Pinball' could not be found`** → the DLL isn't referenced or
  the project didn't build. Confirm the `<Reference>` `HintPath` and that this is a .NET Godot
  project, then Build.
- **It's not in Project ▸ Plugins** → this is a runtime code library, not an editor plugin, so there
  is no enable toggle. Use its classes from C# / as scene nodes.
