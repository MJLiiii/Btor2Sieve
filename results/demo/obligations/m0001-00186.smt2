(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun i_8 () (_ BitVec 4))
(assert
 true)
(assert
 (let (($x140 (and (distinct i_8 (_ bv8 4)) true)))
(not $x140)))
(check-sat)
