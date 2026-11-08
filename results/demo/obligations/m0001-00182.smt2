(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun i_8 () (_ BitVec 4))
(assert
 true)
(assert
 (let (($x91 (and (distinct i_8 (_ bv15 4)) true)))
(not $x91)))
(check-sat)
