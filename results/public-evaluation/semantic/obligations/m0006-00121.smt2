(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun s_3 () (_ BitVec 4))
(assert
 true)
(assert
 (let (($x100 (and (distinct s_3 (_ bv15 4)) true)))
(not $x100)))
(check-sat)
