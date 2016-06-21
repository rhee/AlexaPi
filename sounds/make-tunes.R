#' # make beep tones

#+ include=F
#knitr::opts_chunk$set(echo=T,warning=F,message=F)

#+
#library("dplyr")
library("tuneR") # in a regular session, we are loading tuneR

#try({dev.off()})
par.save = par(mfrow=c(2,2))

#' guestimation
#' - beep1
#' -- 6c#
#' -- 1108.7
#' - beep2
#' -- 5g#
#' -- 830.61

#+
tuneR::setWavPlayer('play')

note <- function(freq,dur){
  
  samp.rate <- 24000
  
  if (0 == dur)
    duration = 1
  else
    duration = samp.rate * dur
  
  if (0 == freq)
    silence(duration = duration, samp.rate = samp.rate)
  else
    sine(freq = freq, duration = duration, samp.rate = samp.rate)
  
}

dur0 <- 0.75
dur1 <- 0.115
dur2 <- 0.005

s1 <- tuneR::bind(
  note(0,dur0),
  note(1108.7,dur1),
  note(0,dur2),
  note(1108.7,dur1),
  note(0,dur2),
  note(1,0))
s1 <- normalize(s1, unit = "16", level = 0.15)
play(s1)

s2 <- tuneR::bind(
  note(0,dur0),
  note(830.61,dur1),
  note(0,dur2),
  note(830.61,dur1),
  note(0,dur2),
  note(1,0))
s2 <- normalize(s2, unit = "16", level = 0.15)
play(s2)

par(mfrow=c(1,2))
plot(s1)
plot(s2)
par(par.save)

tuneR::writeWave(s1,"chime1.wav")
tuneR::writeWave(s2,"chime2.wav")

dur3 <- 0.125
dur4 <- 0.25
s3 <- tuneR::bind(
  note(0,dur0),
  note(440,dur3),
  note(0,dur4),
  note(440,dur3),
  note(0,dur4),
  note(440,dur3),
  note(1,0))
s3 <- normalize(s3, unit = "16", level = 0.15)
play(s3)

tuneR::writeWave(s3,"chime3.wav")

system("lame chime1.wav chime1.mp3; lame chime2.wav chime2.mp3; lame chime3.wav chime3.mp3")

