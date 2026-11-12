using System.Text.Json;
namespace LocalLingua.Launcher;
static class TechnicalLog {
    static readonly object Gate=new();
    public static void Write(string component,string code,int? exitCode=null){
        try{lock(Gate){
            string directory=Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),"LocalLingua","runtime");
            Directory.CreateDirectory(directory);string file=Path.Combine(directory,"launcher.jsonl");
            if(File.Exists(file)&&new FileInfo(file).Length>131072)File.Move(file,file+".1",true);
            File.AppendAllText(file,JsonSerializer.Serialize(new{at=DateTimeOffset.UtcNow,component,code,exitCode})+Environment.NewLine);
        }}catch(IOException){}catch(UnauthorizedAccessException){}
    }
}
