(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun s_6 () (_ BitVec 4))
(declare-fun s_4 () (_ BitVec 4))
(assert
 true)
(assert
 (let (($x291 (and (distinct s_4 s_6) true)))
(not $x291)))
(check-sat)
