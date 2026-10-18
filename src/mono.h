uint8_t monopitch(uint8_t c,uint8_t note){int16_t n=(int16_t)note+((int16_t)monovalue(c,0)-(c==2?1:0))*12;if(n<0)n=0;if(n>127)n=127;return n;}
void monoroute(void){uint8_t c,p,out=0;NR50_REG=master;for(c=0;c<3;c++)if(monovol[c]){p=c==1&&expecho&&expconfig[18]?exppan:monovalue(c,6);if(p!=2)out|=0x10<<c;if(p!=0)out|=1<<c;}NR51_REG=route&out;}
void monorefresh(void){uint8_t c,n;if(!monodown)return;n=monocount?monokeys[monosource[9]?monoarpstep%monocount:monocount-1]:held[0];for(c=0;c<3;c++){if(c==1&&expconfig[15])continue;held[c]=n;basepitch[c]=monopitch(c,n);updatepitch(c);}}
void monopulse(uint8_t c,uint8_t attack){uint16_t base=c?0xff16:0xff11,f=pitchvalue(c);uint8_t level=monovol[c];REG(base)=monovalue(c,4)<<6;REG(base+1)=level?(attack?(8|monovalue(c,2)):((level<<4)|monovalue(c,3))):0;REG(base+2)=f;REG(base+3)=0x80|(f>>8);}
void monoapply(uint8_t c){uint16_t f;uint8_t i,a,shape=monovalue(2,5);if(c==1&&expconfig[15]&&!expconfig[0])return;if(expconfig[0]){if(c<2){monovol[c]=0;stop(c);}else {monovol[2]=((uint16_t)monovalue(2,1)*monovel+63)/127;active[2]=!!monovol[2];exp_waveapply();}return;}if(c==2&&expwaveon){exp_waveapply();monoroute();return;}if(c<2){monovol[c]=((uint16_t)monovalue(c,1)*monovel)/127;monoticks[c]=0;monostage[c]=monovol[c]?(monovalue(c,2)?1:monovalue(c,3)?2:3):0;if(expconfig[19]){monovol[c]=0;monostage[c]=3;}active[c]=!!monovol[c];liveduty[c]=monovalue(c,4);if(!c)NR10_REG=0;if(expconfig[19]){REG(c?0xff17:0xff12)=8;REG(c?0xff19:0xff14)=0x80|(pitchvalue(c)>>8);}else monopulse(c,monostage[c]==1);}
 else{NR30_REG=0;monovol[2]=((uint16_t)monovalue(2,1)*monovel+63)/127;active[2]=!!monovol[2];monostage[2]=active[2]?3:0;
 for(i=0;i<16;i++){if(shape==3){a=i*2;REG(0xff30+i)=((a<monovalue(2,4)?15:0)<<4)|((a+1)<monovalue(2,4)?15:0);}else REG(0xff30+i)=monowaves[shape][i];}
 if(active[2]){f=pitchvalue(2);NR31_REG=0;NR32_REG=(4-monovol[2])<<5;NR33_REG=f;NR30_REG=0x80;NR34_REG=0x80|(f>>8);}}
 monoroute();}
void monostart(uint8_t note,uint8_t vel){uint8_t c,i;modreset();if(!monosource[7])lfophase=lfocycle=0;envstage=1;for(c=0;c<3;c++)for(i=0;i<7;i++)monoeffective[c][i]=monovalue(c,i);monodown=1;monovel=monosource[10]?vel:127;if(expactive)exp_note(note);for(c=0;c<3;c++){if(c==1&&expconfig[15])continue;basepitch[c]=monopitch(c,note);held[c]=note;velocity[c]=vel;phase[c]=age[c]=0;livepitch[c]=basepitch[c];monoapply(c);}}
void monocut(void){uint8_t c;modreset();monodown=0;for(c=0;c<3;c++){monostage[c]=monovol[c]=0;stop(c);held[c]=255;}monoroute();}
void monorelease(void){uint8_t c,tail=0,mask=expactive?exp_off():0;for(c=0;c<3;c++){
 if(mask&(1<<c))continue;
 if(monosource[8]&&monosource[3]&&monodepth[c][1]&&!monoset[c][1])tail=1;
 else if(c!=1||!expecho){monostage[c]=4;monovol[c]=0;stop(c);}}
 if(tail){envstage=4;envfrom=envlevel;envclock=0;modtail=1;return;}
 if(mask)return;
 if(expconfig[0]){monodown=0;return;}monocut();}
void modframe(void){uint8_t duration,target,c,i,changed;int16_t value;uint16_t ticks;uint8_t *depth=&monodepth[0][0];
 if(modtail&&!monosource[8]){monocut();return;}
 if(monosource[8]&&envstage&&envstage!=3){duration=monosource[envstage==1?0:envstage==2?1:3];target=envstage==1?64:envstage==2?monosource[2]:0;ticks=(uint16_t)envclock+frameadvance;if(!duration||ticks>=duration){envlevel=target;envclock=0;envfrom=target;if(envstage==4){envstage=0;if(modtail){monocut();return;}}else envstage++;}else{envclock=ticks;envlevel=envfrom+((int16_t)target-envfrom)*envclock/duration;}}
 if(envstage==3)envlevel=monosource[2];
 if(monosource[5]){ticks=(uint16_t)lfophase+(uint16_t)monosource[5]*frameadvance;lfophase=ticks;lfocycle+=ticks>>8;}

 if(!monodown)return;
 for(c=0;c<21;c++)if(depth[c])break;if(c==21)return;
 for(c=0;c<3;c++){changed=0;for(i=0;i<7;i++){value=monovalue(c,i);if(monoeffective[c][i]!=value){monoeffective[c][i]=value;changed|=1<<i;}}if(changed&1)monorefresh();if((changed&62)&&monostage[c]!=4){ticks=monoticks[c];duration=monostage[c];if(c<2&&!(changed&14))REG(c?0xff16:0xff11)=monovalue(c,4)<<6;else monoapply(c);monoticks[c]=ticks;if(duration)monostage[c]=duration;}}
}
void monoevent(uint8_t t,uint8_t a,uint8_t b){uint8_t i,j;if(t==0x90&&b){for(i=0;i<monocount;i++)if(monokeys[i]==a){for(j=i;j+1<monocount;j++)monokeys[j]=monokeys[j+1];monocount--;break;}if(monocount==8){for(i=0;i<7;i++)monokeys[i]=monokeys[i+1];monocount--;}monokeys[monocount++]=a;monostart(a,b);return;}
 if(t==0x80||(t==0x90&&!b)){for(i=0;i<monocount;i++)if(monokeys[i]==a){for(j=i;j+1<monocount;j++)monokeys[j]=monokeys[j+1];monocount--;break;}if(monocount)monorefresh();else if(!polysustain)monorelease();return;}
 if(t==0xe0){for(i=0;i<3;i++){wheellast[i]=((uint16_t)b<<7)|a;bendupdate(i);}return;}
 if(t!=0xb0)return;
 if(a==64){polysustain=b>=64;if(!polysustain&&!monocount)monorelease();}
 else if(a==120||a==123||a==103){panic();monoroute();}
 /* No preset, engine, CC or poly-handler fallthrough in this test instrument. */
}
void monoframe(void){uint8_t c,s,rate;uint16_t target;if(!monomode)return;if(monosource[9]&&monocount>1){monoarpclock+=(uint16_t)monosource[9]*frameadvance;if(monoarpclock>=60){while(monoarpclock>=60){monoarpclock-=60;monoarpstep++;}monoarpstep%=monocount;monorefresh();if(expactive)exp_note(monokeys[monoarpstep]);for(c=0;c<3;c++)monoapply(c);}}else monoarpclock=monoarpstep=0;modframe();for(c=0;c<2;c++){s=monostage[c];if(s!=1&&s!=2)continue;rate=monovalue(c,s==1?2:3);target=(uint16_t)monovol[c]*rate*60;monoticks[c]+=(uint16_t)frameadvance*64;if(monoticks[c]>=target){monoticks[c]=0;if(s==1){monostage[c]=monovalue(c,3)?2:3;monopulse(c,0);}else{monostage[c]=4;monovol[c]=0;stop(c);}}}if(expactive)exp_frame();monoroute();}
void monoenable(void){uint8_t c;panic();engineset(0);TAC_REG=0;monomode=polymode=1;monoosc%=5;modreset();route=0x77;vin=0;for(c=0;c<3;c++){param[c][8]=0;param[c][25]=monosource[6];}param[2][8]=param[2][9]=param[2][17]=param[2][22]=0;globals();if(expactive)exp_changed();monoroute();dirty=1;}
