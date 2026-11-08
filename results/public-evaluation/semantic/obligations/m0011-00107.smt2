(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun s_6 () (_ BitVec 4))
(assert
 true)
(assert
 (let (($x209 (and (distinct s_6 (_ bv15 4)) true)))
(not $x209)))
(check-sat)
