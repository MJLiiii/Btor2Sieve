(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun s_4 () (_ BitVec 4))
(declare-fun s_3 () (_ BitVec 4))
(assert
 true)
(assert
 (let (($x1388 (and (distinct s_3 s_4) true)))
(not $x1388)))
(check-sat)
