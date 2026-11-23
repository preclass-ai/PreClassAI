/**
 * Runs in <head> before the bundle: Chrome fires `beforeinstallprompt` early, often before the dashboard's chunk has
 * loaded, so the event is kept on window and `pc-install` tells the React side (src/lib/pwa.ts) it changed.
 * Also marks <html class="pc-standalone"> when the app was opened from the home screen.
 * Kept in a plain module (no "use client") so the server layout can inline the string.
 */
export const PWA_BOOT_SCRIPT = `(function(){try{var w=window,d=document.documentElement;var sa=function(){try{return matchMedia("(display-mode: standalone)").matches||matchMedia("(display-mode: minimal-ui)").matches||navigator.standalone===true}catch(e){return false}};if(sa())d.classList.add("pc-standalone");w.addEventListener("beforeinstallprompt",function(e){e.preventDefault();w.__pcInstall=e;w.dispatchEvent(new Event("pc-install"))});w.addEventListener("appinstalled",function(){w.__pcInstall=null;w.__pcInstalled=true;w.dispatchEvent(new Event("pc-install"))})}catch(e){}})();`;
