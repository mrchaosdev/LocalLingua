import fs from 'node:fs';
import path from 'node:path';
const output=process.argv[2];fs.mkdirSync(output,{recursive:true});
const inventory=[],seen=new Set();
function inspect(directory) {
  if(!fs.existsSync(directory))return;
  for(const name of fs.readdirSync(directory)) {
    if(name.startsWith('.'))continue;
    const folder=path.join(directory,name);
    if(name.startsWith('@')){inspect(folder);continue;}
    const manifest=path.join(folder,'package.json');
    if(!fs.existsSync(manifest))continue;
    const pkg=JSON.parse(fs.readFileSync(manifest,'utf8'));
    const key=`${pkg.name}@${pkg.version}`;
    if(!seen.has(key)) {
      seen.add(key);const destination=path.join(output,pkg.name.replaceAll('/','__')+'-'+pkg.version);
      fs.mkdirSync(destination,{recursive:true});
      const licenses=fs.readdirSync(folder).filter(file=>/^(license|notice|copying)/i.test(file)&&fs.statSync(path.join(folder,file)).isFile());
      for(const file of licenses)fs.copyFileSync(path.join(folder,file),path.join(destination,file));
      inventory.push({name:pkg.name,version:pkg.version,license:pkg.license,repository:pkg.repository,licenseFiles:licenses});
    }
    inspect(path.join(folder,'node_modules'));
  }
}
inspect('node_modules');fs.writeFileSync(path.join(output,'inventory.json'),JSON.stringify(inventory,null,2));
