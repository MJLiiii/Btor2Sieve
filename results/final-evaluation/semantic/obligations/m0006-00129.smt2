(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun s_3 () (_ BitVec 4))
(assert
 true)
(assert
 (let (($x763 (and (distinct s_3 (_ bv7 4)) true)))
(not $x763)))
(check-sat)
