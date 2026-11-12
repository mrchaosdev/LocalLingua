using System.Runtime.InteropServices;
using System.Windows.Interop;
using System.Text.Json;

namespace LocalLingua.Overlay;
static class Desktop {
    public const int WmHotkey=0x0312;
    [StructLayout(LayoutKind.Sequential)] public struct Rect {public int Left,Top,Right,Bottom;}
    [StructLayout(LayoutKind.Sequential)] struct MonitorInfo {public int Size;public Rect Monitor,Work;public uint Flags;}
    delegate bool MonitorCallback(IntPtr monitor,IntPtr hdc,IntPtr rectangle,IntPtr data);
    [DllImport("user32.dll")] static extern bool EnumDisplayMonitors(IntPtr hdc,IntPtr clip,MonitorCallback callback,IntPtr data);
    [DllImport("user32.dll")] static extern bool GetMonitorInfoW(IntPtr monitor,ref MonitorInfo info);
    [DllImport("user32.dll")] public static extern bool RegisterHotKey(IntPtr hwnd,int id,uint modifiers,uint key);
    [DllImport("user32.dll")] public static extern bool UnregisterHotKey(IntPtr hwnd,int id);
    [DllImport("user32.dll",EntryPoint="GetWindowLongW")] static extern int GetWindowLong(IntPtr hwnd,int index);
    [DllImport("user32.dll",EntryPoint="SetWindowLongW")] static extern int SetWindowLong(IntPtr hwnd,int index,int value);
    [DllImport("user32.dll")] static extern bool GetWindowRect(IntPtr hwnd,out Rect rect);
    [DllImport("user32.dll")] static extern bool SetWindowPos(IntPtr hwnd,IntPtr after,int x,int y,int width,int height,uint flags);
    public static List<Rect> WorkAreas() {
        var result=new List<Rect>();
        EnumDisplayMonitors(IntPtr.Zero,IntPtr.Zero,(monitor,_,_,_)=>{var info=new MonitorInfo{Size=Marshal.SizeOf<MonitorInfo>()};if(GetMonitorInfoW(monitor,ref info))result.Add(info.Work);return true;},IntPtr.Zero);
        return result;
    }
    public static void ClickThrough(IntPtr hwnd,bool enabled) {
        int style=GetWindowLong(hwnd,-20);
        SetWindowLong(hwnd,-20,enabled?style|0x20:style&~0x20);
    }
    public static void NextMonitor(IntPtr hwnd) {
        var screens=WorkAreas();if(screens.Count==0)return;
        GetWindowRect(hwnd,out var current);
        int index=screens.FindIndex(s=>current.Left>=s.Left&&current.Left<s.Right&&current.Top>=s.Top&&current.Top<s.Bottom);
        var target=screens[(index+1)%screens.Count];int width=current.Right-current.Left,height=current.Bottom-current.Top;
        SetWindowPos(hwnd,IntPtr.Zero,target.Left+Math.Max(0,(target.Right-target.Left-width)/2),target.Bottom-height-40,0,0,0x15);
    }
    static string PathName=>System.IO.Path.Combine(Environment.GetEnvironmentVariable("LOCALLINGUA_DATA_DIR")??System.IO.Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),"LocalLingua"),"overlay-window.json");
    public static void Save(IntPtr hwnd) {
        if(!GetWindowRect(hwnd,out var rect))return;
        try {
            System.IO.Directory.CreateDirectory(System.IO.Path.GetDirectoryName(PathName)!);
            System.IO.File.WriteAllText(PathName+".tmp",JsonSerializer.Serialize(new[]{rect.Left,rect.Top,rect.Right-rect.Left,rect.Bottom-rect.Top}));
            System.IO.File.Move(PathName+".tmp",PathName,true);
        }catch(System.IO.IOException){}
    }
    public static void Restore(IntPtr hwnd) {
        try {
            var value=JsonSerializer.Deserialize<int[]>(System.IO.File.ReadAllText(PathName));
            if(value is null||value.Length!=4||value[2]<390||value[3]<150)return;
            var screens=WorkAreas();
            if(!screens.Any(s=>value[0]>=s.Left&&value[0]+value[2]<=s.Right&&value[1]>=s.Top&&value[1]+value[3]<=s.Bottom))return;
            SetWindowPos(hwnd,IntPtr.Zero,value[0],value[1],value[2],value[3],0x14);
        }catch(Exception e) when(e is System.IO.IOException or JsonException){}
    }
}
