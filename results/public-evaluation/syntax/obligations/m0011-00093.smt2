(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun s_4 () (_ BitVec 4))
(assert
 true)
(assert
 (let (($x496 (and (distinct s_4 (_ bv7 4)) true)))
(not $x496)))
(check-sat)
